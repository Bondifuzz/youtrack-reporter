import re
from typing import TYPE_CHECKING, Optional

from mqtransport.participants import Consumer, Producer
from mqtransport import MQApp
from pydantic import BaseModel, AnyHttpUrl, ConstrainedStr

from mqtransport.errors import ConsumeMessageError

from youtrack_reporter.app.errors import YouTrackError
from youtrack_reporter.app.youtrack import YTIssue
from youtrack_reporter.app.database.errors import DatabaseError

if TYPE_CHECKING:
    from .state import MQAppState

class LabelStr(ConstrainedStr):
    min_length = 1
    curtail_length = 255


class DescriptionStr(ConstrainedStr):
    min_length = 1
    curtail_length = 28000


class CrashInfoStr(ConstrainedStr):
    min_length = 1
    curtail_length = 1000

class MC_DuplicateCrashFound(Consumer):

    """Send notification to youtrack that duplicate of crash is found"""

    name: str = "youtrack-reporter.crashes.duplicate"

    class Model(BaseModel):

        config_id: str
        """ Unique config id used to find integration """

        crash_id: str
        """ Unique id of crash """

        duplicate_count: int
        """ Count of similar crashes found (at least) """

    async def consume(self, msg: Model, app: MQApp):
        state: MQAppState = app.state

        try:
            config = await state.db.configs.get(msg.config_id)
        except DatabaseError as e:
            self.logger.error(f"Can't find youtrack config with id: {msg.config_id}")
            await state.producers.youtrack_report_undelivered.produce(
                config_id=msg.config_id,
                error=str(e)
            )
            return
        
        try:
            issue_id = await state.db.issues.get_issue(msg.crash_id)
        except DatabaseError as e:
            self._logger.error("Can't update non-created issue!")
            await state.producers.youtrack_report_undelivered.produce(
                config_id=msg.config_id,
                error=str(e)
            )
            return
        
        issue: YTIssue = YTIssue(id=issue_id)
        
        try:
            description = await state.youtrack_api.get_issue_description(config, issue)
            print(description)
            description = re.sub(
                r"\*Duplicates\*: [0-9]+", 
                f"*Duplicates*: {msg.duplicate_count}",
                description
            )
            await state.youtrack_api.update_issue(config, issue, description)
        except YouTrackError as e:
            await state.producers.youtrack_report_undelivered.produce(
                config_id=msg.config_id,
                error=str(e)
            )
        


class MC_UniqueCrashFound(Consumer):

    """Send notification to youtrack that unique crash is found"""

    name: str = "youtrack-reporter.crashes.unique"

    class Model(BaseModel):

        config_id: str
        """ Unique config id used to find integration """

        crash_id: str
        """ Unique id of crash """

        crash_info: CrashInfoStr
        """ Short description for crash """

        crash_type: LabelStr
        """ Type of crash: crash, oom, timeout, leak, etc.. """

        crash_output: DescriptionStr
        """ Crash output (long multiline text) """

        crash_url: AnyHttpUrl # TODO: len
        """ URL can be opened to read crash information """

        project_name: LabelStr
        """ Name of project. Used for grouping YT issues """

        fuzzer_name: LabelStr
        """ Name of fuzzer. Used for grouping YT issues """

        revision_name: LabelStr
        """ Name of fuzzer revision. Used for grouping YT issues """

    async def consume(self, msg: Model, app: MQApp):
        state: MQAppState = app.state

        try:
            config = await state.db.configs.get(msg.config_id)
        except DatabaseError as e:
            self.logger.error(f"Can't find youtrack config with id: {msg.config_id}")
            await state.producers.youtrack_report_undelivered.produce(
                config_id=msg.config_id,
                error=str(e)
            )
            return

        self._logger.debug(("Consumed message:\ncrash_id: %s\n"
                           "crash url: %s\ncrash info: %s\n"
                           "crash type: %s\ncrash output: %s\n"
                           "project name: %s\nfuzzer name: %s\n"
                           "revision name: %s"),
                          msg.crash_id, msg.crash_url, msg.crash_info, 
                          msg.crash_type, msg.crash_output,
                          msg.project_name, msg.fuzzer_name,
                          msg.revision_name)

        description = f'''
        *Crash info*: {msg.crash_info}
        *Crash link*: {msg.crash_url}
        *Project name*: {msg.project_name}
        *Fuzzer name*: {msg.fuzzer_name}
        *Revision*: {msg.revision_name}
        *Duplicates*: 0
        *Full output*: ```{msg.crash_output}```
        '''

        try:
            issue: YTIssue = await state.youtrack_api.create_issue(
                config=config,
                summary=msg.crash_info[:255],
                description=description
            )
            await state.db.issues.insert(msg.crash_id, issue.id)
        except YouTrackError as e:
            await state.producers.youtrack_report_undelivered.produce(
                config_id=msg.config_id,
                error=str(e)
            )


class MP_YTIntegrationResult(Producer):
    name = "youtrack-reporter.integrations.result"

    class Model(BaseModel):
        config_id: str
        """ Unique config id used to find integration """

        error: Optional[str]
        """ Last error caused integration to fail """

        update_rev: str
        """ Update revision. Used to filter outdated messages """

class MP_YTReportUndelivered(Producer):
    name = "youtrack-reporter.reports.undelivered"

    class Model(BaseModel):
        config_id: str
        """ Unique config id used to find integration """

        error: str
        """ Last error caused integration to fail """
