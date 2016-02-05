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

    def checkResult(self):
        for resultfile in self.results:
            if 'creationtime' not in resultfile: 
                continue
            xmldoc = minidom.parse(resultfile)
            tclist = xmldoc.getElementsByTagName('TestCase')
            for tc in tclist:
                #print(tc.attributes['name'].value)
                tflist = tc.getElementsByTagName('TestFunction')
                for tf in tflist:
                    if 'initTestCase' in tf.attributes['name'].value or 'cleanupTestCase' in tf.attributes['name'].value:
                        continue
                    print(tf.attributes['name'].value)
                    brlist = tf.getElementsByTagName('BenchmarkResult')
                    for br in brlist:
                        print('tag:' + br.attributes['tag'].value
                              + ', metric:' + br.attributes['metric'].value
                              + ', value:' + br.attributes['value'].value
                              + ', iterations:' + br.attributes['iterations'].value
                              )
        
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
        p = subprocess.Popen(['git', 'log', '-1', '--pretty=format:%H'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return out

    def test(self):
        print(','.join(self.modules))
        print('make -j9 module-' + ' module-'.join(self.modules))
                        
if __name__ == "__main__":
        runner = QtQuickControls2BenchmarksRunner()
        runner.fetchGitRepository()
        if runner.getSha1():
           if runner.build():
               runner.buildAndRunTest()
               print(','.join(runner.results))
               runner.saveResults()
