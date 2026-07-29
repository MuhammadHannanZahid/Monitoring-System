from app.modules.website.schemas import WebsiteResponse
from app.shared.models.website import WebsiteModel

class WebsiteMapper:
    @staticmethod
    def to_response(website: WebsiteModel) -> WebsiteResponse:
        return WebsiteResponse(
            id=website.id,
            name=website.name,
            url=website.url,
            check_interval=website.check_interval,
            timeout=website.timeout,
            expected_status_code=website.expected_status_code,
            status=website.status,
            is_active=website.is_active,
            created_at=website.created_at,
            updated_at=website.updated_at,
            last_checked_at=website.last_checked_at,
        )

    @staticmethod
    def to_response_list(websites: list[WebsiteModel]) -> list[WebsiteResponse]:
        return [
            WebsiteMapper.to_response(website)
            for website in websites
        ]