from ais.task import Task
from pprint import pprint
import logging

class AVT(Task):

    def run(self, **kwargs):
        logging.info("%s class ran its task" % self.name)

        
    def respond(self, event):
        job = event.job
        logging.info("Job {0} has run {1} times".format(job.name, job.runs))
        logging.info("Last run for {0} was at {1}".format(job.name,
            event.scheduled_run_time))
        