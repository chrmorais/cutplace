"""
Development reports for cutplace.
"""
import cgi
import coverage
import cProfile
import dev_colorize
import keyword
import logging
import optparse
import os
import pstats
import StringIO
import sys
import tools
import unittest

_log = logging.getLogger("cutplace.dev_reports")

def _testLotsOfCustomers():
    import test_cutplace
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_cutplace.LotsOfCustomersTest)
    unittest.TextTestRunner(verbosity=2).run(suite)

def _getSourceFolder():
    return os.path.join("source", "cutplace")

def _listdirPythonSource():
    return tools.listdirMatching(_getSourceFolder(), ".*\\.py")

def _addToKeyList(map, key, valueToAdd):
    if map.has_key(key):
        map[key].append(valueToAdd)
    else:
        map[key] = [valueToAdd]
        
def createProfilerReport(targetBasePath):
    assert targetBasePath is not None
    
    itemName = "profile_lotsOfCustomers"
    targetProfilePath = os.path.join(targetBasePath, itemName) + ".profile"
    targetReportPath = os.path.join(targetBasePath, itemName) + ".txt"
    cProfile.run("_testLotsOfCustomers()", targetProfilePath)
    targetReportFile = open(targetReportPath, "w")
    try:
        stats = pstats.Stats(targetProfilePath, stream=targetReportFile)
        stats.sort_stats("cumulative").print_stats("cutplace", 20)
    finally:
        targetReportFile.close()

def createTasksReport(targetBasePath):
    assert targetBasePath is not None
    TASK_IDS = ["FIXME", "TODO", "HACK"]
    
    taskHtmlPath = os.path.join(targetBasePath, "tasks.html")
    _log.info("write %r" % taskHtmlPath)

    modulePaths = [os.path.join(_getSourceFolder(), fileName) for fileName in _listdirPythonSource()]
    taskTypeToTexts = {}
    taskTypeCount = {}
    # Collect tasks in module source codes
    for modulePath in modulePaths:
        moduleName = os.path.split(modulePath)[1]
        moduleFile = open(modulePath, "r")
        try:
            lineNumber = 0
            for line in moduleFile:
                lineNumber += 1
                for taskId in [id + ":" for id in TASK_IDS]:
                    taskIdIndex = line.find(taskId)
                    if taskIdIndex >= 0:
                        taskType = line[taskIdIndex:taskIdIndex + len(taskId) - 1]
                        taskText = line[taskIdIndex + len(taskId):].strip()
                        _addToKeyList(taskTypeToTexts, taskType, (moduleName, lineNumber, taskText))
                        _log.debug("%s::%s" % (taskType, taskText))
        finally:
            moduleFile.close()
    # Render HTML report.
    taskHtml = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
    <head>
        <title>Cutplace Tasks</title>
    </head>
    <body>
        <h1>Cutplace Tasks</h1>
        <table>"""
    for taskType in TASK_IDS:
        if taskTypeToTexts.has_key(taskType):
            taskTexts = taskTypeToTexts[taskType]
            taskHtml += "            <h2>%s</h2>" % cgi.escape(taskType)
            taskHtml += "            <table>"
            for (moduleName, lineNumber, taskText) in taskTexts:
                # TODO: Add source location
                taskHtml += "            <tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (cgi.escape(moduleName), lineNumber, cgi.escape(taskText))
            taskHtml += "            </table>"
    taskHtml += """    </body>
</html>"""
    # Write task report.
    taskHtmlFile = open(taskHtmlPath, "w")
    try:
        taskHtmlFile.write(taskHtml)
    finally:
        taskHtmlFile.close()
    
def createCoverageReport(targetBasePath):
    # Collect coverage data.
    print "collecting coverage data"
    coverage.erase()
    coverage.start()
    import tools
    modules = []
    # Note: in order for this to work the script must run from project folder.
    moduleFilesNames = _listdirPythonSource()
    # Strip folder and extension from names
    moduleNames = [os.path.splitext(os.path.split(fileName)[1])[0] for fileName in moduleFilesNames]
    # FIXME: Figure out why we have duplicates and remove the hack below.
    moduleNames = set(moduleNames)
    # Remove "dev_" modules.
    moduleNames = [moduleName for moduleName in moduleNames if not moduleName.startswith("dev_")]
    moduleNames.sort()
    for moduleName in moduleNames:
        modules.append(__import__(moduleName))
    import test_all
    test_all.main()
    createProfilerReport(baseFolder)
    coverage.stop()

    # Create report.
    coverageHtml = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
    <head>
        <title>Cutplace Test Coverage</title>
    </head>
    <body>
        <h1>Cutplace Test Coverage</h1>
        <table>"""
        
    for module in modules:
        f, s, m, mf = coverage.analysis(module)
        coverageHtmlName = "coverage_" + os.path.basename(f) + ".html"
        targetHtmlPath = os.path.join(targetBasePath, coverageHtmlName)
        coverageHtml += "<tr><td><a href=\"%s\">%s</a></td>" % (coverageHtmlName, os.path.basename(f))
        reportStringIO = StringIO.StringIO()
        try:
            coverage.report(module, file=reportStringIO)
            reportStringIO.seek(0)
            moduleCoverageReport = reportStringIO.read()
            coverageHtml += "<td><pre>%s</pre></td></tr>" % cgi.escape(moduleCoverageReport)
        finally:
            reportStringIO.close() 
        print "write %r" % targetHtmlPath
        fo = file(targetHtmlPath, "wb")
        # colorization
        dev_colorize.colorize_file(f, outstream=fo, not_covered=mf)
        fo.close()
    coverageHtml += """        </table>
    </body>
</html>"""
    coverageHtmlFile = open(os.path.join(targetBasePath, "coverage.html"), "w")
    try:
        coverageHtmlFile.write(coverageHtml)
    finally:
        coverageHtmlFile.close()
    # print report on stdout
    # coverage.report(urllib2)
    # erase coverage data
    coverage.erase()

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger("cutplace").setLevel(logging.WARNING)
    logging.getLogger("cutplace.dev_reports").setLevel(logging.INFO)

    usage = "usage: %prog FOLDER"
    parser = optparse.OptionParser(usage)
    options, others = parser.parse_args()
    if len(others) == 1:
        baseFolder = others[0]
        createCoverageReport(baseFolder)
        createTasksReport(baseFolder)
    else:
        sys.stderr.write("%s%s" % ("target folder for reports must be specified", os.linesep))
        sys.exit(1)
        