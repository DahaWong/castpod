import datetime
from callbacks import job as callback

def set_jobs(job_queue):
    job_queue.run_repeating(
        callback = callback.update_podcasts, 
        interval = datetime.timedelta(seconds= 3),
        name =  callback.update_podcasts.__name__
    )