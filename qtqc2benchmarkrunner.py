#!/usr/bin/python

import os, sys
import shutil
import subprocess
from xml.dom import minidom

def touch(fname, times=None):
    fhandle = open(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

class QtQuickControls2BenchmarksRunner:

    def __init__(self):
        self.package = ''
        self.basedir = os.path.expanduser('~') + '/tmp/benchmarks'
        self.sourcedir = self.basedir + '/git'
        self.builddir = self.basedir + '/build'
        self.buildlock = self.builddir + '/.lock'
        self.resultdir = self.basedir + '/results'
        self.modules = ['qtbase', 'qtxmlpatterns', 'qtsvg', 'qtdeclarative', 'qtgraphicaleffects', 'qtquickcontrols', 'qtquickcontrols2']
        self.sha1s = list()
        self.results = list()

    def initGitRepository(self):
        if os.path.exists(self.sourcedir):
            shutil.rmtree(self.sourcedir)
        os.system('mkdir ' + self.sourcedir)
        os.chdir(self.sourcedir)
        os.system('git clone git://code.qt.io/qt/qt5.git')
        os.chdir(self.sourcedir + '/qt5')
        os.system('git checkout 5.6')
        os.system('./init-repository -f --module-subset=' + ','.join(self.modules) + ' --branch 5.6')
        
    def fetchGitRepository(self):
        if not os.path.exists(self.sourcedir + '/qt5'):
            self.initGitRepository()
        os.chdir(self.sourcedir + '/qt5')
        for module in self.modules:
            os.chdir(self.sourcedir + '/qt5/' + module)
            os.system('git pull')
        
    def build(self):
        if os.path.exists(self.buildlock):
            print('building lock file exists!')
            return False
            
        if len(self.sha1s) != len(self.modules):
            print('sth is wrong, sha1s don\'t match modules!')
            return False
            
        qtqc2sha1 = self.sha1s[len(self.sha1s) - 1]
        targetdir = self.resultdir + '/' + qtqc2sha1
        if os.path.exists(targetdir):
            print(targetdir + ' folder exists! not build any more')
            return False

        if os.path.exists(self.builddir):
            shutil.rmtree(self.builddir)
        os.system('mkdir ' + self.builddir)
        os.chdir(self.builddir)
        touch(self.buildlock)
        os.system('mkdir qt5-build')
        os.chdir(self.builddir + '/qt5-build')
        os.system('../../git/qt5/configure -developer-build -confirm-license -opensource -release -nomake tests -nomake examples')
        os.system('make -j9 module-' + ' module-'.join(self.modules))
        if os.path.exists(self.buildlock):
            os.remove(self.buildlock)
        return True
        
    def buildAndRunTest(self):
        os.chdir(self.builddir + '/qt5-build/qtquickcontrols2')
        os.system('make -j9 sub-tests')
        testdir = self.builddir + '/qt5-build/qtquickcontrols2/tests/benchmarks'
        os.chdir(testdir)
        lists = os.listdir(testdir)
        for item in lists:
            itemdir = testdir + '/' + item
            if os.path.isdir(itemdir) == True:
                os.chdir(itemdir)
                resultfilename = 'result-tst_' + item + '.xml'
                resultfile = itemdir + '/' + resultfilename
                if os.path.exists(resultfile):
                    os.remove(resultfile)
                os.system('./tst_' + item + ' -xml -o ' + resultfilename)
                if os.path.exists(resultfile):
                    self.results.append(resultfile)

    def checkResult(self, resultfile, tag, r_tags, r_values):
        xmldoc = minidom.parse(resultfile)
        tclist = xmldoc.getElementsByTagName('TestCase')
        for tc in tclist:
            #print(tc.attributes['name'].value)
            tflist = tc.getElementsByTagName('TestFunction')
            for tf in tflist:
                if 'initTestCase' in tf.attributes['name'].value or 'cleanupTestCase' in tf.attributes['name'].value:
                    continue
                #print('test: ' + tf.attributes['name'].value)
                if tf.attributes['name'].value != tag:
                    continue
                brlist = tf.getElementsByTagName('BenchmarkResult')
                brsize = len(brlist)
                #print('brsize:' + str(brsize))
                if len(r_tags) == 0:
                    r_tags = range(brsize)
                values = range(brsize)
                index = 0
                for br in brlist:
                    tag = br.attributes['tag'].value
                    value = br.attributes['value'].value
                    if tag in r_tags:
                        idx = r_tags.index(tag)
                        values[idx] = value
                    else:
                        r_tags[index] = tag
                        values[index] = value
                    index = index + 1
                    # print('tag:' + br.attributes['tag'].value
                    #         + ', metric:' + br.attributes['metric'].value
                    #         + ', value:' + br.attributes['value'].value
                    #         + ', iterations:' + br.attributes['iterations'].value
                    #         )
                r_values.append(values)
        return (r_tags, r_values)
        
    def getSha1(self):
        result = True
        for module in self.modules:
            modulepath = self.sourcedir + '/qt5/' + module
            if not os.path.exists(modulepath):
                print('warning: ' + modulepath + ' doesn\'t exist!')
                result = False
            else:
                self.sha1s.append(self.getLatestSha1(modulepath))
        return result
        
    def saveResults(self):
        if not os.path.exists(self.resultdir):
            os.chdir(self.basedir)
            os.system('mkdir results')
        os.chdir(self.resultdir)
        if len(self.sha1s) != len(self.modules):
            print('sth is wrong, didn\'t get correct sha1s!')
            return False
        #print('len:' + str(len(self.sha1s)))
        #print('qtqc2 sha1:' + self.sha1s[len(self.sha1s) - 1])
        qtqc2sha1 = self.sha1s[len(self.sha1s) - 1]
        targetdir = self.resultdir + '/' + qtqc2sha1
        if os.path.exists(targetdir):
            print(targetdir + ' folder exists!')
            return False
        os.system('mkdir ' + qtqc2sha1)
        for resultfile in self.results:
            shutil.copy(resultfile, targetdir)
                
    def getLatestSha1(self, modulepath, num=1, fmt='%H'):
        os.chdir(modulepath)
        p = subprocess.Popen(['git', 'log', '-' + str(num), '--pretty=format:' + fmt, '--date=short'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out

    def test(self):
        print(','.join(self.modules))
        print('make -j9 module-' + ' module-'.join(self.modules))

    def getSha1s(self, num=1, fmt='%H'):
        rsha1s = list()
        rdates = list()
        sha1s = self.getLatestSha1(self.sourcedir + '/qt5/qtquickcontrols2', num, fmt)
        #print('sha1s are ' + sha1s)
        sha1list = sha1s.splitlines(sha1s.count('\n'))
        for sha1 in reversed(sha1list):
            sha1 = sha1.rstrip()
            #print('sha1 is ' + sha1)
            tmp = sha1.split(' ')
            if len(tmp) < 2:
                continue
            resultfile = self.resultdir + '/' + tmp[0] + '/result-tst_creationtime.xml';
            if os.path.exists(resultfile):
                rsha1s.append(tmp[0])
                rdates.append(tmp[1])
        return (rsha1s, rdates)

    def analyzer1(self, r_sha1s, tag):
        r_tags = list()
        r_values = list()
        for sha1 in r_sha1s:
            sha1 = sha1.rstrip()
            #print('sha1 is ' + sha1)
            resultfile = self.resultdir + '/' + sha1 + '/result-tst_creationtime.xml';
            if os.path.exists(resultfile):
                #print('found result file in ' + resultfile)
                r_tags, r_values = self.checkResult(resultfile, tag, r_tags, r_values)
        result = ' = [\n'
        result = result + '[ \'sha1s\', \'' + '\' , \''.join(r_sha1s) + '\' ],\n'
        index = 0
        vlen = len(r_values)
        #print('vlen:' + str(vlen))
        for tag in r_tags:
            if index != 0:
                result = result + ', '
            result = result + '[ \'' + tag + '\', '
            for vindex, values in enumerate(r_values, start=0):   # default is zero
                result = result + values[index]
                #print('vindex:' + str(vindex))
                if vindex < vlen-1:
                    result = result + ', '
            result = result + ' ]\n'
            index = index + 1
        result = result + '];\n'
        #print(result)
        return result

    def analyzer2(self, r_sha1s, r_dates, tag):
        r_tags = list()
        r_values = list()
        r_labels = list()
        index = 0
        for sha1 in r_sha1s:
            sha1 = sha1.rstrip()
            #print('sha1 is ' + sha1)
            resultfile = self.resultdir + '/' + sha1 + '/result-tst_creationtime.xml';
            if os.path.exists(resultfile):
                #print('found result file in ' + resultfile)
                r_tags, r_values = self.checkResult(resultfile, tag, r_tags, r_values)
                r_labels.append(r_dates[index] + ' ' + sha1[0:7])
                index = index + 1
        result = ' = [\n'
        result = result + '[ \'tags\', \'' + '\' , \''.join(r_tags) + '\' ],\n'
        index = 0
        for label in r_labels:
            if index != 0:
                result = result + ', '
            result = result + '[ \'' + label + '\', ' + ','.join(r_values[index]) + ' ]\n'
            index = index + 1
        result = result + '];\n'
        #print(result)
        return result

    def analyzerAll(self):
        r_sha1s, r_dates = self.getSha1s(100, '%H %cd')
        if not r_sha1s:
            print('warning: analyzerAll() didn\'t get any sha1 back!')
            return
        print('sha1s: ' + ','.join(r_sha1s))
        print('dates: ' + ','.join(r_dates))
        t_sha1s = list()
        t_sha1s.append(r_sha1s[len(r_sha1s)-1])
        category = ['controls', 'material', 'universal', 'calendar']
        for c in category:
            s = 'var mydata' + self.analyzer1(t_sha1s, c)
            sfn = self.resultdir + '/latest-' + c + '.js'
            jsfile = open(sfn, "w")
            jsfile.write(s)
            jsfile.close()
            s = 'var mydata' + self.analyzer2(r_sha1s, r_dates, c)
            sfn = self.resultdir + '/' + c + '.js'
            jsfile = open(sfn, "w")
            jsfile.write(s)
            jsfile.close()
                        
if __name__ == "__main__":
        runner = QtQuickControls2BenchmarksRunner()
        runner.fetchGitRepository()
        if runner.getSha1():
           if runner.build():
               runner.buildAndRunTest()
               print(','.join(runner.results))
               runner.saveResults()
#        runner.analyzerAll()
