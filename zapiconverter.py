#!/usr/bin/env python

import time
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree
import json
import os

baseURL = 'https://jira-uat.test.com'
projectId = '10201'
versionId = '51152'
versionName = 'REL_23.00'
date = time.strftime("%Y-%m-%d")
results_location = 'C:\\temp\\soap_results\\TEST-SOAP_TestCases.xml'
results_path = 'C:\\temp\\regression\\'
csv_file = 'testlist.csv'
test_cycle = 'Web Services Regression'
test_cycle_desc = 'Regression results created using ZAPI'
username = 'username'
password = 'Password123'

#Create new Test Cycle
def createCycle():
    print "Creating a new Test Cycle plan...."
    createCycleURL = baseURL + '/rest/zapi/latest/cycle'

    payload = \
        {
        "name": test_cycle,
        "description": test_cycle_desc,
        "startDate": date,
        "endDate": date,
        "projectId": projectId,
        "versionId": versionId
        }
    headers = {'content-type': 'application/json' }
    response = requests.post(createCycleURL, json=payload,
                         auth=HTTPBasicAuth(username, password), headers=headers, verify=False)


    print response.content
    if (response.status_code == 200):
        print "Response status code: " + str(response.status_code)
        print "Test Cycle Plan created"
        print response.url
        data = response.json()
        cycleId=data['id']
        print "Cycle ID: " + cycleId
        return cycleId
    else:
        print "Response status code: " + str(response.status_code)
        print "!Error creating Test Cycle Plan"
        print response.url
        print response.raise_for_status()

#Creates tests from SOAPUI results
def createTests():
    print "Creating tests from parsed SOAPUI results..."
    try:
        e = xml.etree.ElementTree.parse(results_location).getroot()
    except IOError:
        print "File reading/parsing error"
    createTestURL = baseURL + '/rest/api/2/issue/'
    count=0
    testList=[]

    for testcase in e.findall('testcase'):
        print "Test name: " + (testcase.get('name'))
        payload = \
            {
                "fields": {
                    "project":
                        {
                            "key": "EGIS"
                        },
                    "summary": (testcase.get('name')),
                    "description": "",
                    "issuetype": {
                        "name": "Test"
                    }
                }
            }
        headers = {'content-type': 'application/json'}
        response = requests.post(createTestURL, json=payload,
                                 auth=HTTPBasicAuth(username, password), headers=headers, verify=False)
        print response.content
        if (response.status_code == 201):
            print "Response status code: " + str(response.status_code)
            print "Test case created!"
            print response.url
            data = response.json()
            jiraId = data['id']
            print "Jira ID: " + jiraId
            count +=1
            testList.insert(count, jiraId) #Add Jira ID's to a list

        else:
            print "Response status code: " + str(response.status_code)
            print "!Error creating Test Case"
            print response.url
            print response.raise_for_status()

    print "***Added " + str(count)  + " test cases.***"

    print "Test case ID's: " + str(testList)
    file = open (csv_file, 'wb')
    print >> file, ','.join(testList)
    return [x.encode('UTF8') for x in testList] #decode unicode in python



def updateExecution(cycleId, testList, testStatusList):
    print "Adding tests to the cycle plan and then updating execution results...."
    executionURL = baseURL + '/rest/zapi/latest/execution/'

    headers = {'content-type': 'application/json' }

    testResultsdict = dict(zip(testList, testStatusList)) #create dictionary with test ID"s with test status lists
    print testResultsdict

    for k,v in testResultsdict.iteritems():

        values = {"status": v}
        payload = \
            {
                "issueId": k,
                "versionId": versionId,
                "cycleId": cycleId,
                "projectId": projectId
            }
        print "Payload: " + str(payload)
        updateResponse = requests.post(executionURL, json=payload,
                         auth=HTTPBasicAuth(username,password), headers=headers, verify = False)
        print updateResponse.content

        if(updateResponse.status_code == 200):
            print "Response status code: " + str(updateResponse.status_code)
            print "Test case " + k + " added to cycle: " + str(cycleId)
            print updateResponse.url
#            data = updateResponse.json()
            data = json.loads(str(updateResponse.text))
            for id in data:
                testId = id
            print "Test ID: " + testId
        else:
            print "Error during test case addition"
            updateResponse.raise_for_status()

        newExecuteURL = executionURL + testId + '/execute'
        print newExecuteURL
        print "Status value: " + str(v)
        execResponse = requests.put(newExecuteURL, json=values,
                             auth=HTTPBasicAuth(username, password), headers=headers, verify = False)

        print "Status Code: " + str(execResponse.status_code)

        if(execResponse.status_code == 200):
            print "Test case execution updated"
            print execResponse.url

        else:
            print "Error during test case execution update"
            print "Status Code: " + str(execResponse.status_code)
            print execResponse.content
            print execResponse.url
            execResponse.raise_for_status()


    print "*************Completed Test execution update!!!***********************"


def getIssueId(testName):
#    summary = 'Testing ZAPI'

    jiraIdURL = baseURL + '/rest/api/2/search?jql=summary~%22%5C%22Testing+ZAPI%5C%22%22&project=EGIS&fields=(id%2Ctype%2Ckey%2Csummary%2Cproject)&maxResults=5'

    headers = {'content-type': 'application/json'}
    idResponse = requests.get(jiraIdURL,
                                auth=HTTPBasicAuth(username, password), headers=headers, verify=False)
    print idResponse.content

    if (idResponse.status_code == 200):
        print idResponse.url
        data = idResponse.json()
        issues = data['issues'][0]
        issueId = issues['id']
        print "Test ID: " + str(issueId)
        return issueId
    else:
        print "Failed to get JIRA ID"
        print "Status Code: " + str(idResponse.status_code)
        print idResponse.url
        idResponse.raise_for_status()

#Parses SOAPUI XML results
def parseResults():
    print "Parsing SOAPUI test results...."
    testResults = {}
    testStatusList = []


    for filename in os.listdir(results_path):
        if not filename.endswith('.xml'): continue
        cnt = 0  # count
        fullname = os.path.join(results_path, filename)
        print "Test Suite: " + fullname
        try:
            e = xml.etree.ElementTree.parse(fullname).getroot()
        except IOError:
            print "File reading/parsing error"
        for testcase in e.findall('testcase'):

            testName = testcase.get('name')
            print "Test Name: " + testName

            failure = testcase.find('failure')
            if failure is not None:
                testResults[testName] = 'Failed'
                testStatusList.insert(cnt,"2")
                print "Failed: " + str(failure.get("message"))
            else:
                testResults[testName] = 'Passed'
                testStatusList.insert(cnt, "1")
            cnt += 1

            print "Count element: " + str(cnt)

    print "Test Results: " + str(testResults)
    print len(testResults)
    print "Test Results status list: " + str(testStatusList)
    print len(testStatusList)

    return testStatusList

def updateExecutionOnly(cycleId, testStatusList):

    print "Adding tests to the cycle plan and then updating execution results...."
    executionURL = baseURL + '/rest/zapi/latest/execution/'

    headers = {'content-type': 'application/json' }

    file = open(csv_file, 'r')
    strings = file.read().split(',')
    strings[-1] = strings[-1].strip()
    print strings

    tList = list(strings)

    print tList
    print len(tList)
    file.close()

    testResultsDict = dict(zip(tList, testStatusList)) #create dictionary with test ID"s with status lists
    print testResultsDict

    for k,v in testResultsDict.iteritems():

        values = {"status": v}
        payload = \
            {
                "issueId": k,
                "versionId": versionId,
                "cycleId": cycleId,
                "projectId": projectId
            }
        print "Payload: " + str(payload)
        updateResponse = requests.post(executionURL, json=payload,
                         auth=HTTPBasicAuth(username,password), headers=headers, verify = False)
        print updateResponse.content

        if(updateResponse.status_code == 200):
            print "Response status code: " + str(updateResponse.status_code)
            print "Test case " + k + " added to cycle: " + str(cycleId)
            print updateResponse.url
#            data = updateResponse.json()
            data = json.loads(str(updateResponse.text))
            for id in data:
                testId = id
            print "Test ID: " + testId
        else:
            print "Error during test case addition"
            updateResponse.raise_for_status()

        newExecuteURL = executionURL + testId + '/execute'
        print newExecuteURL
        print "Status value: " + str(v)
        execResponse = requests.put(newExecuteURL, json=values,
                             auth=HTTPBasicAuth(username, password), headers=headers, verify = False)
#        print execResponse.content
        print "Status Code: " + str(execResponse.status_code)

        if(execResponse.status_code == 200):
            print "Test case execution updated"
            print execResponse.url

        else:
            print "Error during test case execution update"
            print "Status Code: " + str(execResponse.status_code)
            print execResponse.content
            print execResponse.url
            execResponse.raise_for_status()

    print "\n"
    print "\n"
    print "*************Completed Test execution update for " + str(len(tList)) + " test cases!!!***********************"





def main():


    parseResults()
    createTests()
#    getIssueId('Testing ZAPI')

#    updateExecution(createCycle(),createTests(),parseResults())
#    updateExecutionOnly(createCycle(), parseResults())

#    parseResults()

main()





