from datetime import datetime, timezone
from app.modules.website.repository import WebsiteRepository
from app.shared.constants import Messages
from app.shared.enums import WebsiteStatus
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.models.website import WebsiteModel
from app.core.logger import get_logger

logger = get_logger(__name__)

class WebsiteService:
    def __init__(self, repository: WebsiteRepository):
        self.repository = repository

    async def create_website(self, name: str, url: str, check_interval: int, timeout: int, expected_status_code: int) -> WebsiteModel:
        existing_url = await self.repository.get_by_url(url)
        if existing_url is not None:
            logger.warning("Attempted to create website with existing URL '%s'.", url)
            raise ConflictError(Messages.WEBSITE_ALREADY_EXISTS)

        count = await self.repository.count_similar_names(name)
        final_name = name

        if count > 0:
            final_name = f"{name} {count}"
            logger.info("Website name '%s' already exists. Assigned new name '%s'.", name, final_name)

        now = datetime.now(timezone.utc)

        website = WebsiteModel(
            name=final_name,
            url=url,
            check_interval=check_interval,
            timeout=timeout,
            expected_status_code=expected_status_code,
            status=WebsiteStatus.UNKNOWN,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_checked_at=None,
        )

        website.id = await self.repository.create_website(website)
        logger.info("Website '%s' created. URL: %s", website.name, website.url)
        return website

    async def list_websites(self) -> list[WebsiteModel]:
        return await self.repository.list_websites()

    async def get_website(self, website_id: str) -> WebsiteModel:
        website = await self.repository.get_by_id(website_id)
        if website is None:
            logger.warning("Requested website '%s' was not found.", website_id)
            raise NotFoundError(Messages.WEBSITE_NOT_FOUND)
        return website

    async def update_website(self, website_id: str, name: str | None, url: str | None, check_interval: int | None, timeout: int | None, expected_status_code: int | None) -> WebsiteModel:
        website = await self.get_website(website_id)
        update_data = {}
        if name is not None and name != website.name:
            count = await self.repository.count_similar_names(name)
            if count > 0:
                final_name = f"{name} {count}"
                logger.info("Website name '%s' already exists. Assigned new name '%s' during update for website ID %s.", name, final_name, website_id)
                update_data["name"] = final_name
            else:
                update_data["name"] = name

        if url is not None and url != website.url:
            existing_url = await self.repository.get_by_url(url)
            if existing_url is not None and str(existing_url.id) != str(website_id):
                logger.warning("Attempted to update website '%s' with existing URL '%s'.", website.name, url)
                raise ConflictError(Messages.WEBSITE_ALREADY_EXISTS)
            update_data["url"] = url

        if check_interval is not None and check_interval != website.check_interval:
            update_data["check_interval"] = check_interval

        if timeout is not None and timeout != website.timeout:
            update_data["timeout"] = timeout

        if expected_status_code is not None and expected_status_code != website.expected_status_code:
            update_data["expected_status_code"] = expected_status_code

        if update_data:
            await self.repository.update_website(website_id, update_data)
            updated_website = await self.get_website(website_id)
            logger.info("Website '%s' updated. Fields changed: %s", updated_website.name, ", ".join(update_data.keys()))
            return updated_website

        return website

    async def delete_website(self, website_id: str) -> None:
        website = await self.get_website(website_id)
        await self.repository.delete_website(website.id)
        logger.info("Website '%s' deleted.", website.name)

    async def activate_website(self, website_id: str) -> WebsiteModel:
        website = await self.get_website(website_id)
        await self.repository.set_active(website.id, True)
        logger.info("Website '%s' activated.", website.name)
        return await self.get_website(website_id)

    async def deactivate_website(self, website_id: str) -> WebsiteModel:
        website = await self.get_website(website_id)
        await self.repository.set_active(website.id, False)
        logger.info("Website '%s' deactivated.", website.name)
        return await self.get_website(website_id)