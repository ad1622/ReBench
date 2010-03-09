# Copyright (c) 2009 Stefan Marr <http://www.stefan-marr.de/>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import with_statement

import logging
import subprocess
#import math
import time
from Statistics import StatisticProperties

from contextpy import layer, activelayers, after,before
# proceed, activelayer, around, base, globalActivateLayer, globalDeactivateLayer

benchmark = layer("benchmark")
profile = layer("profile")
quick   = layer("quick")

class Executor:
    
    def __init__(self, configurator, dataAggregator, reporter = None):
        self._configurator = configurator
        self._data = dataAggregator
        self._reporter = reporter
        self._jobs = [] # the list of configurations to be executed
                
    def _construct_cmdline(self, bench_cfg, perf_reader, cores, input_size, variable):
        cmdline  = ""
        cmdline += "cd %s && "%(bench_cfg.suite['location'])
        
        if bench_cfg.suite['ulimit']:
            cmdline += "ulimit -t %s && "%(bench_cfg.suite['ulimit'])
                
        if self._configurator.options.use_nice:
            cmdline += "sudo nice -n-20 "
        
        vm_cmd = "%s/%s %s" % (bench_cfg.vm['path'],
                               bench_cfg.vm['binary'],
                               bench_cfg.vm.get('args', "") % {'cores' : cores})
            
        vm_cmd = perf_reader.acquire_command(vm_cmd)
            
        cmdline += vm_cmd 
        cmdline += bench_cfg.suite['command'] % {'benchmark':bench_cfg.name, 'input':input_size, 'variable':variable}
        
        if bench_cfg.extra_args is not None:
            cmdline += " %s" % (bench_cfg.extra_args or "")
        
        return cmdline
    
    def _exec_configuration(self, cfg, cores, input_size, var_val):
        runId = (cfg, cores, input_size, var_val)
        
        perf_reader = self._get_performance_reader_instance(cfg.performance_reader)
        
        cmdline = self._construct_cmdline(cfg,
                                          perf_reader,
                                          cores,
                                          input_size,
                                          var_val)
        
        logging.debug("command = " + cmdline)
            
        terminate = False
        error = (0, 0)  # (consequent_erroneous_runs, erroneous_runs)
        
        while not terminate:
            terminate, error = self._generate_data_point(cmdline, error, perf_reader, runId)
            logging.debug("Run: #%d"%(self._data.getNumberOfDataPoints(runId)))
                
        #self._consolidate_result(bench_name, input_size)
        
        
        # TODO add here some user-interface stuff to show progress
    
    
        self.reporter.report(self.result[self.current_vm][self.num_cores][input_size],
                             self.current_vm, self.num_cores, input_size)
        
        
        
    def _consolidate_result(self, bench_name, input_size):
        results = {}
        
        for run in self.current_data:
            for result in run[1]:
                bench = result['bench'] + "-" + result.get('subCriterion', "")
                values = results.get(bench, [])
                values.append(result['time'])
                results[bench] = values
        
        for bench_name, values in results.iteritems():
            result = self._confidence(values, 
                                      self.config["statistics"]['confidence_level'])
            self.result[self.current_vm][self.num_cores][input_size][bench_name] = result
            
            (mean, sdev, interval_details, interval_details_t) = result 
            logging.debug("Run completed for %s:%s (size: %s, cores: %d), mean=%f, sdev=%f"%(self.current_vm, bench_name, input_size, self.num_cores, mean, sdev))
    
    def _get_performance_reader_instance(self, reader):
        p = __import__("performance", fromlist=reader)
        return getattr(p, reader)()

    @before(benchmark)
    def _exec_vm_run(self, input_size):
        logging.debug("Statistic cfg: min_runs=%s, max_runs=%s"%(self.config["statistics"]["min_runs"],
                                                                 self.config["statistics"]["max_runs"]))
        
        
    def _generate_data_point(self, cmdline, error, perf_reader, runId):
        (consequent_erroneous_runs, erroneous_runs) = error
        p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (output, _) = p.communicate()
        
        (cnf, _, _, _) = runId
        
        if p.returncode != 0:
            consequent_erroneous_runs += 1
            erroneous_runs += 1
            logging.warning("Run #%d of %s:%s failed"%(self._data.getNumberOfDataPoints(runId),
                                                       cnf.vm['name'], cnf.name))
        else:
            logging.debug(u"Output: %s"%(output))
            self._eval_output(output, perf_reader, consequent_erroneous_runs, erroneous_runs)
        
        return self._check_termination_condition(runId, consequent_erroneous_runs, erroneous_runs)
    
    def _eval_output(self, output, perf_reader, consequent_erroneous_runs, erroneous_runs):
        pass
    
    @after(benchmark)
    def _eval_output(self, output, perf_reader, consequent_erroneous_runs, erroneous_runs, __result__):
        exec_time = perf_reader.parse_data(output)
        if exec_time[0] is None:
            consequent_erroneous_runs += 1
            erroneous_runs += 1
            logging.warning("Run of %s:%s failed"%(self.current_vm, self.current_benchmark))
        else:    
            #self.benchmark_data[self.current_vm][self.current_benchmark].append(exec_time)
            self.current_data.append(exec_time)
            consequent_erroneous_runs = 0
            logging.debug("Run %s:%s result=%s"%(self.current_vm, self.current_benchmark, exec_time[0]))
        
    def _check_termination_condition(self, runId, consequent_erroneous_runs, erroneous_runs):
        return False, (consequent_erroneous_runs, erroneous_runs)
    
    @after(profile)
    def _check_termination_condition(self, runId, consequent_erroneous_runs, erroneous_runs, __result__):
        return True, (consequent_erroneous_runs, erroneous_runs)
    
    @after(benchmark)
    def _check_termination_condition(self, runId, consequent_erroneous_runs, erroneous_runs, __result__):
        terminate, (consequent_erroneous_runs, erroneous_runs) = __result__
        
        numDataPoints = self._data.getNumberOfDataPoints(runId)
        (cfg, _, _, _) = runId
        
        if consequent_erroneous_runs >= 3:
            logging.error("Three runs of %s have failed in a row, benchmark is aborted"%(cfg.name))
            terminate = True
        elif erroneous_runs > numDataPoints / 2 and erroneous_runs > 6:
            logging.error("Many runs of %s are failing, benchmark is aborted."%(cfg.name))
            terminate = True
        elif numDataPoints >= self._configurator.statistics["max_runs"]:
            logging.debug("Reached max_runs for %s"%(cfg.name))
            terminate = True
        elif (numDataPoints >= self._configurator.statistics["min_runs"]
              and self._confidence_reached(runId)):
            logging.debug("Confidence is reached for %s"%(cfg.name))
            terminate = True
        
        return terminate, (consequent_erroneous_runs, erroneous_runs)
    
    @after(quick)
    def _check_termination_condition(self, runId, consequent_erroneous_runs, erroneous_runs, __result__):
        terminate, (consequent_erroneous_runs, erroneous_runs) = __result__
        
        (cfg, _, _, _) = runId
        
        if len(self.current_data) >= self.config["quick_runs"]["max_runs"]:
            logging.debug("Reached max_runs for %s"%(cfg.name))
            terminate = True
        elif (len(self.current_data) > self.config["quick_runs"]["min_runs"]
              and sum(self.current_data)  / (1000 * 1000) > self.config["quick_runs"]["max_time"]):
            logging.debug("Maximum runtime is reached for %s"%(cfg.name))
            terminate = True
        
        return terminate, (consequent_erroneous_runs, erroneous_runs)
   
                
    def _confidence_reached(self, runId):
        
        stats = StatisticProperties(self._data.getDataSet(runId),
                                    self._configurator.statistics['confidence_level'])
        
        
        
        logging.debug("Run: %d, Mean: %f, current error: %f, Interval: [%f, %f]"%(
                      stats.numSamples, stats.mean,
                      stats.confIntervalSize, stats.confIntervalLow, stats.confIntervalHigh))
        
        if stats.confIntervalSize < self._configurator.statistics["error_margin"]:
            return True
        else:
            return False
    
    def _generate_all_configs(self, benchConfigs):
        result = []
        
        for cfg in benchConfigs:
            for cores  in cfg.vm['cores']:
                for input_size in cfg.suite['input_sizes']:
                    for var_val in cfg.suite['variable_values']:
                        result.append((cfg, cores, input_size, var_val))
        
        return result
    
    def execute(self):
        startTime = None
        runsCompleted = 0
        (actions, benchConfigs) = self._configurator.getBenchmarkConfigurations()
        configs = self._generate_all_configs(benchConfigs)
        
        runsRemaining = len(configs)
        
        for action in actions:
            with activelayers(layer(action)):
                for (cfg, cores, input_size, var_val) in configs:
                    self._reporter.info("Configurations left: %d"%(runsRemaining))
                    
                    if runsCompleted > 0:
                        current = time.time()
                        
                        etl = (current - startTime) / runsCompleted * runsRemaining
                        sec = etl % 60
                        min = (etl - sec) / 60 % 60
                        h   = (etl - sec - min) / 60 / 60
                        self._reporter.info("Estimated time left: %02d:%02d:%02d"%(round(h), round(min), round(sec)))
                    else:
                        startTime = time.time()
                    
                    self._exec_configuration(cfg, cores, input_size, var_val)
                    
                    runsCompleted = runsCompleted + 1
