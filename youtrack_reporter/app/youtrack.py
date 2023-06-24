from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List
from pydantic import BaseModel
import pydantic
from .errors import *
from logging import Logger

import logging
import aiohttp

if TYPE_CHECKING:
    from app.database.orm import ORMConfig

class YTProject(BaseModel):
    id: str
    name: str

class YTIssue(BaseModel):
    id: str

class YouTrackAsyncAPI:
    _logger: Logger

    client: aiohttp.ClientSession
    config: ORMConfig
    headers: Dict[str, str]

    def __init__(self):
        self._logger = logging.getLogger("YouTrack")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.client = aiohttp.ClientSession(headers=self.headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo):
        if self.client:
            await self.client.close()

    async def get_project_id(self, config: ORMConfig) -> str:

        params = {"query": config.project, "fields": "id,name"}
        url = f"{config.url}/api/admin/projects"
        auth_header = {"Authorization": f"Bearer {config.token}"}

        self._logger.debug(f"Request info: url={url}, params={params}, method = GET")

        async with self.client.get(url=url, params=params, headers=auth_header) as resp:
            if resp.status != 200:
                self._logger.error(f"Server response code is not OK: {resp.status}; resp.text = {await resp.text()}")
                raise ResponseStatusError(resp.status)
            
            try:
                json = await resp.json()
            except ValueError as e:
                self._logger.error(f"Asyncio lib failed to parse resp as json: {await resp.text()}")
                raise ResponseParseError("JSON parsing failed")

            if not isinstance(json, list):
                self._logger.error(f"Failed to parse response. Reason - wrong json format: {await resp.text()}")
                raise ResponseParseError("JSON was not parsed correctly")

            self._logger.debug(f"{resp.request_info}, resp.json = {json}")

            proj = None
            for i in json:
                if i['name'] == config.project:
                    proj = i
                break

            if proj is None:
                self._logger.error(f"Specified project was not found. Project name: {config.project}")
                raise ProjectNotFound(config.project)

            try:
                project = YTProject.parse_obj(proj)
                return project.id
            except pydantic.ValidationError as e:
                self._logger.error(f"Response can't be parsed to pydantic model object: {await resp.text()}")
                raise ResponseParseError(f"Pydantic model parsing failed")
                

    async def validate_credentials(self, config: ORMConfig) -> ORMConfig:
        url = f"{config.url}/api/admin/projects"
        auth_header = {"Authorization": f"Bearer {config.token}"}
        self._logger.debug(f"Request info: url={url}, auth={auth_header}, method = GET")

        try:
            config.project_id = await self.get_project_id(config)
            self._logger.debug(f"Project was found, id = {config.project_id}")
            issue = await self.create_issue(config, "test issue", "test issue")
            self._logger.debug(f"Issue {issue} was created")
            await self.delete_issue(config, issue)
        except YouTrackError as e:
            raise e

        return config

    async def create_issue(self, config: ORMConfig, summary: str, description: str) -> YTIssue:
        try:
            # May be unnecessary check, should examine
            if config.project_id is None:
                config.project_id = await self.get_project_id(config)
            
            data = {
                "project": {"id": config.project_id},
                "summary": summary,
                "description": description,
            }
            url = f"{config.url}/api/issues"
            auth_header = {"Authorization": f"Bearer {config.token}"}
            
            self._logger.debug(f"Request info: url={url}, json={data}, method = POST")
            async with self.client.post(url=url, json=data, headers=auth_header) as resp:
                if resp.status != 200:
                    self._logger.error(f"Response status in not OK: {resp.status}; resp.text = {await resp.text()}")
                    raise ResponseStatusError(resp.status)
                
                try:
                    json = await resp.json()
                except ValueError as e:
                    self._logger.error(f"Asyncio lib failed to parse resp as json: {await resp.text()}")
                    raise ResponseParseError("JSON parsing failed")
                
                if not isinstance(json, dict):
                    self._logger.error(f"Failed to parse response. Reason - wrong json format: {await resp.text()}")
                    raise ResponseParseError("JSON was not parsed correctly")
                
                try:
                    issue = YTIssue.parse_obj(json)
                    return issue
                except pydantic.ValidationError as e:
                    self._logger.error(f"Response can't be parsed to pydantic model object: {await resp.text()}")
                    raise ResponseParseError(f"Pydantic model parsing failed")

        except YouTrackError as e:
            self._logger.error(f"Failed to create issue. Config: {config.dict(exclude={'token'})}")
            raise e

    async def update_issue(self, config: ORMConfig, issue: YTIssue, description: str) -> YTIssue:
        try:
            data = {
                "project": {"id": config.project_id},
                "description": description
            }
            url = f"{config.url}/api/issues/{issue.id}"
            auth_header = {"Authorization": f"Bearer {config.token}"}

            self._logger.debug(f"Request info: url={url}, json={data}, method = POST")
            async with self.client.post(url=url, json=data, headers=auth_header) as resp:
                if resp.status != 200:
                    self._logger.error(f"Response status in not OK: {resp.status}; resp.text = {await resp.text()}")
                    raise ResponseStatusError(resp.status)

                try:
                    json = await resp.json()
                except ValueError as e:
                    self._logger.error(f"Asyncio lib failed to parse resp as json: {await resp.text()}")
                    raise ResponseParseError("JSON parsing failed")
                
                if not isinstance(json, dict):
                    self._logger.error(f"Failed to parse response. Reason - wrong json format: {await resp.text()}")
                    raise ResponseParseError("JSON was not parsed correctly")
                
                try:
                    issue = YTIssue.parse_obj(json)
                    return issue
                except pydantic.ValidationError as e:
                    self._logger.error(f"Response can't be parsed to pydantic model object: {await resp.text()}")
                    raise ResponseParseError(f"Pydantic model parsing failed")
        except YouTrackError as e:
            self._logger.error(f"Failed to update issue. Config: {config.dict(exclude={'token'})}, issue: {issue.dict()}")
            raise e

    async def get_issue_description(self, config: ORMConfig, issue: YTIssue) -> str:
        try:
            params = {"fields": "description"}
            url = f"{config.url}/api/issues/{issue.id}"
            auth_header = {"Authorization": f"Bearer {config.token}"}

            self._logger.debug(f"Request info: url={url}, method = GET")

            async with self.client.get(url=url, params=params, headers=auth_header) as resp:
                if resp.status != 200:
                    self._logger.error(f"Server response code is not OK: {resp.status}; resp.text = {await resp.text()}")
                    raise ResponseStatusError(resp.status)
                
                try:
                    json = await resp.json()
                except ValueError as e:
                    self._logger.error(f"Asyncio lib failed to parse resp as json: {await resp.text()}")
                    raise ResponseParseError("JSON parsing failed")

                if not isinstance(json, dict):
                    self._logger.error(f"Failed to parse response. Reason - wrong json format: {await resp.text()}")
                    raise ResponseParseError("JSON was not parsed correctly")

                try:
                    return json['description']
                except KeyError as e:
                    self._logger.error(f"Failed to get issue description: field description is not in the responce")
                    raise ResponseParseError("Wrong responce format")

        except YouTrackError as e:
            self._logger.error(f"Failed to get issue description. Config: {config.dict(exclude={'token'})}")


    async def delete_issue(self, config: ORMConfig, issue: YTIssue) -> None:
        url = f"{config.url}/api/issues/{issue.id}"
        auth_header = {"Authorization": f"Bearer {config.token}"}
        
        self._logger.debug(f"Request info: url={url}, method = DELETE")
        async with self.client.delete(url=url, headers=auth_header) as resp:
            if resp.status != 200:
                self._logger.error(f"Error while deleting issue. Server response code is not OK: {resp.status}; resp.text = {await resp.text()}")
                raise ResponseStatusError(resp.status)