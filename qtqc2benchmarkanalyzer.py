#!/usr/bin/python

import os, sys
import shutil
import subprocess
from xml.dom import minidom

class QtQuickControls2BenchmarksAnalyzer:

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
        self.r_tags = list()
        self.r_sha1s = list()
        self.r_values = list()
        
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

    def checkResult(self, resultfile):
        xmldoc = minidom.parse(resultfile)
        tclist = xmldoc.getElementsByTagName('TestCase')
        for tc in tclist:
            #print(tc.attributes['name'].value)
            tflist = tc.getElementsByTagName('TestFunction')
            for tf in tflist:
                if 'initTestCase' in tf.attributes['name'].value or 'cleanupTestCase' in tf.attributes['name'].value:
                    continue
                print('test: ' + tf.attributes['name'].value)
                if tf.attributes['name'].value != 'controls':
                    continue
                brlist = tf.getElementsByTagName('BenchmarkResult')
                brsize = len(brlist)
                print('brsize:' + str(brsize))
                if len(self.r_tags) == 0:
                    self.r_tags = range(brsize)
                values = range(brsize)
                index = 0
                for br in brlist:
                    tag = br.attributes['tag'].value
                    value = br.attributes['value'].value
                    if tag in self.r_tags:
                        idx = self.r_tags.index(tag)
                        values[idx] = value
                    else:
                        self.r_tags[index] = tag
                        values[index] = value
                    index = index + 1
                    # print('tag:' + br.attributes['tag'].value
                    #         + ', metric:' + br.attributes['metric'].value
                    #         + ', value:' + br.attributes['value'].value
                    #         + ', iterations:' + br.attributes['iterations'].value
                    #         )
                self.r_values.append(values)
        
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
                
    def getLatestSha1(self, modulepath):
        os.chdir(modulepath)
        p = subprocess.Popen(['git', 'log', '-100', '--pretty=format:%H'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out

    def test(self):
        print(','.join(self.modules))
        print('make -j9 module-' + ' module-'.join(self.modules))
                        
if __name__ == "__main__":
        analyzer = QtQuickControls2BenchmarksAnalyzer()
        sha1s = analyzer.getLatestSha1(analyzer.sourcedir + '/qt5/qtquickcontrols2')
        #print('sha1s are ' + sha1s)
        sha1list = sha1s.splitlines(sha1s.count('\n'))
        for sha1 in reversed(sha1list):
            sha1 = sha1.rstrip()
            #print('sha1 is ' + sha1)
            resultfile = analyzer.resultdir + '/' + sha1 + '/result-tst_creationtime.xml';
            if os.path.exists(resultfile):
                analyzer.r_sha1s.append(sha1)
                #print('found result file in ' + resultfile)
                analyzer.checkResult(resultfile)
        result = 'var data = [\n'
        result = result + '[ \'sha1s\', \'' + '\' , \''.join(analyzer.r_tags) + '\' ],\n'
        index = 0
        for values in analyzer.r_values:
            if index != 0:
                result = result + ', '
            result = result + '[ \'' + analyzer.r_sha1s[index] + '\', ' + ' , '.join(values) + ']\n'
            index = index + 1
        result = result + '];\n'
        print(result)
