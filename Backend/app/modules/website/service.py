from datetime import datetime, timezone
from app.modules.website.repository import WebsiteRepository
from app.shared.constants import Messages
from app.shared.enums import WebsiteStatus
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.models.website import WebsiteModel

class WebsiteService:
    def __init__(self, repository: WebsiteRepository):
        self.repository = repository

    async def create_website(self, name: str, url: str, check_interval: int, timeout: int, expected_status_code: int) -> WebsiteModel:
        existing_url = await self.repository.get_by_url(url)
        if existing_url is not None:
            raise ConflictError(Messages.WEBSITE_ALREADY_EXISTS)

        count = await self.repository.count_similar_names(name)
        final_name = name

        if count > 0:
            final_name = f"{name} {count}"

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
        return website

    async def list_websites(self) -> list[WebsiteModel]:
        return await self.repository.list_websites()

    async def get_website(self, website_id: str) -> WebsiteModel:
        website = await self.repository.get_by_id(website_id)
        if website is None:
            raise NotFoundError(Messages.WEBSITE_NOT_FOUND)
        return website

    async def update_website(self, website_id: str, name: str | None, url: str | None, check_interval: int | None, timeout: int | None, expected_status_code: int | None) -> WebsiteModel:
        website = await self.get_website(website_id)
        update_data = {}
        if name is not None:
            update_data["name"] = name

        if url is not None:
            update_data["url"] = url

        if check_interval is not None:
            update_data["check_interval"] = check_interval

        if timeout is not None:
            update_data["timeout"] = timeout

        if expected_status_code is not None:
            update_data["expected_status_code"] = expected_status_code

        if update_data:
            await self.repository.update_website(website_id, update_data)
        return await self.get_website(website_id)

    async def delete_website(self, website_id: str) -> None:
        website = await self.get_website(website_id)
        await self.repository.delete_website(website.id)

    async def activate_website(self, website_id: str) -> WebsiteModel:
        website = await self.get_website(website_id)
        await self.repository.set_active(website.id, True)
        return await self.get_website(website_id)

    async def deactivate_website(self, website_id: str) -> WebsiteModel:
        website = await self.get_website(website_id)
        await self.repository.set_active(website.id, False)
        return await self.get_website(website_id)