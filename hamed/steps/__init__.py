#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class BaseTask(object):
    NOT_STARTED = 'not-started'
    STARTED = 'started'
    SUCCESS = 'success'
    FAILED = 'failed'
    REVERTING = 'reverting'
    REVERTED = 'reverted'
    ERROR = 'error'

    STATUSES = OrderedDict([
        (NOT_STARTED, "Not started"),
        (STARTED, "Started. In progress"),
        (SUCCESS, "Completed successfuly"),
        (FAILED, "Failed to complete. Not reverted"),
        (REVERTING, "Failed. Reverting in progress"),
        (REVERTED, "Reverted"),
        (ERROR, "Failed to revert properly"),
    ])

    CLEAN_STATUSES = [NOT_STARTED, SUCCESS, REVERTED, ERROR]

    # name = "Anonymous Task"
    status = NOT_STARTED
    processing_exception = None
    reverting_exception = None
    kwargs = {}
    output = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @property
    def name(self):
        return type(self).__name__

    @property
    def successful(self):
        return self.status == self.SUCCESS

    @property
    def reverted(self):
        return self.status == self.REVERTED

    @property
    def clean_state(self):
        return self.status in self.CLEAN_STATUSES

    @property
    def exception(self):
        if self.status in (self.FAILED, self.REVERTING, self.REVERTED):
            return self.processing_exception
        elif self.status == self.ERROR:
            return self.reverting_exception
        else:
            return None

    def update_status(self, status):
        self.status = status


class Task(BaseTask):

    required_inputs = []
    required_outputs = []

    def process(self):
        logger.debug("PROCESSING {}".format(self.name))

        try:
            self.update_status(self.STARTED)

            # ensure any required data is present
            for key in self.required_inputs:
                assert key in self.kwargs.keys()

            self._process()

            # ensure all required output has been created
            for key in self.required_outputs:
                assert key in self.output.keys()

        except Exception as exp:
            logger.error("Exception while processing {}".format(self.name))
            logger.exception(exp)
            self.processing_exception = exp
            self.update_status(self.FAILED)
            self.revert()
        else:
            logger.info("Successful completion of {}".format(self.name))
            self.update_status(self.SUCCESS)

    def revert(self):
        logger.debug("REVERTING {}".format(self.name))

        try:
            self.update_status(self.REVERTING)
            self._revert()
        except Exception as exp:
            logger.error("Exception while reverting {}".format(self.name))
            logger.exception(exp)
            self.reverting_exception = exp
            self.update_status(self.ERROR)
        else:
            logger.info("Successfuly reverted {}".format(self.name))
            self.update_status(self.REVERTED)

    def _process(self):
        pass

    def _revert(self):
        pass

    def release_from_output(self, key):
        if key in self.output:
            del(self.output[key])


class TaskFailed(Exception):
    pass


class TaskCollection(BaseTask):
    tasks = []

    def __init__(self, **kwargs):
        super(TaskCollection, self).__init__(**kwargs)
        self.instances = []
        self.inputs = kwargs

    def process(self):
        self.update_status(self.STARTED)

        try:
            for index, task_cls in enumerate(self.tasks):
                logger.debug("Initiating Task #{}".format(index))

                # should never happen unless task is improperly written
                try:
                    task = task_cls(**self.inputs)
                except Exception as exp:
                    logger.error("Failed to instanciate task (!). reverting.")
                    logger.exception(exp)

                # keep reference of task so we can revert it if required
                self.instances.append(task)

                # process task or raise to stop loop and revert
                try:
                    task.process()
                    assert task.status == task.SUCCESS
                except Exception as exp:
                    if task.processing_exception:
                        exp = task.processing_exception
                    logger.error(
                        "Failed to process task #{}: {}".format(index, exp))
                    self.processing_exception = exp
                    raise TaskFailed()
                else:
                    # update outputs to include task's output
                    self.inputs.update(task.output)
                    self.output.update(task.output)
                    logger.info("Successfuly processed task #{}".format(index))
        except TaskFailed:
            self.revert(index)
        else:
            logger.info("Successfuly processed task collection {}"
                        .format(self.name))
            self.update_status(self.SUCCESS)

    def revert(self, index):
        logger.info("Reverting Task Colection {}".format(self.name))
        self.update_status(self.REVERTING)

        try:
            for rb_index in range(index, -1, -1):
                logger.debug("Calling revert on task #{}".format(rb_index))
                task = self.instances.pop()
                if task.status not in (self.REVERTED, self.REVERTING,
                                       self.ERROR):
                    try:
                        task.revert()
                    except Exception as exp:
                        self.reverting_exception = exp
                        logger.error("Failed to revert task #{}."
                                     .format(rb_index))
                        raise TaskFailed()
                    else:
                        logger.debug("Reverted task #{}".format(rb_index))
        except TaskFailed:
            logger.error("Error while reverting. Improper state at index {}"
                         .format(rb_index))
            self.update_status(self.ERROR)
        else:
            logger.info("Successfuly reverted task collection {}"
                        .format(self.name))
            self.update_status(self.REVERTED)

    def revert_all(self):
        self.update_status(self.REVERTING)

        # instanciate all tasks (without processing them)
        try:
            for index, task_cls in enumerate(self.tasks):
                logger.debug("Initiating Task #{}".format(index))

                # should never happen unless task is improperly written
                try:
                    task = task_cls(**self.inputs)
                except Exception as exp:
                    logger.error("Failed to instanciate task (!). reverting.")
                    logger.exception(exp)

                # keep reference of task so we can revert it if required
                self.instances.append(task)
        except Exception as exp:
            logger.error("Error while reverting all of {}".format(self.name))
            logger.exception(exp)
            self.update_status(self.ERROR)
            return

        # call revert on last task
        self.revert(len(self.instances) - 1)
