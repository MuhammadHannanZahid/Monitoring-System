from fastapi import APIRouter, Depends
from app.modules.HTTP_monitor.dependencies import get_website_service
from app.modules.HTTP_monitor.schemas import CreateHTTP_monitorRequest, UpdateWebsiteRequest, WebsiteResponse
from app.modules.HTTP_monitor.service import HTTP_monitorService
from app.shared.authorization import require_admin
from app.shared.constants import Messages
from app.shared.mappers.website_mapper import WebsiteMapper
from app.shared.responses import SuccessResponse, success_response

router = APIRouter(prefix="/websites", tags=["Websites"], dependencies=[Depends(require_admin())])

@router.post("/create", response_model=SuccessResponse[WebsiteResponse])
async def create_HTTP_monitor(request: CreateHTTP_monitorRequest, service: HTTP_monitorService = Depends(get_website_service)):
    website = await service.create_HTTP_monitor(
        name=request.name,
        url=request.url,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_status_code=request.expected_status_code,
    )

    return success_response(
        message=Messages.WEBSITE_CREATED,
        data=WebsiteMapper.to_response(website),
    )

@router.get("/list_all", response_model=SuccessResponse[list[WebsiteResponse]])
async def list_websites(service: HTTP_monitorService = Depends(get_website_service)):
    websites = await service.list_websites()

    return success_response(
        message=Messages.WEBSITES_FETCHED,
        data=WebsiteMapper.to_response_list(websites),
    )

@router.get("/{website_id}/get_one", response_model=SuccessResponse[WebsiteResponse])
async def get_website(website_id: str, service: HTTP_monitorService = Depends(get_website_service)):
    website = await service.get_website(website_id)

    return success_response(
        message=Messages.WEBSITE_FETCHED,
        data=WebsiteMapper.to_response(website),
    )

@router.put("/{website_id}/update", response_model=SuccessResponse[WebsiteResponse])
async def update_website(website_id: str, request: UpdateWebsiteRequest, service: HTTP_monitorService = Depends(get_website_service)):
    website = await service.update_website(
        website_id=website_id,
        name=request.name,
        url=request.url,
        check_interval=request.check_interval,
        timeout=request.timeout,
        expected_status_code=request.expected_status_code,
    )

    return success_response(
        message=Messages.WEBSITE_UPDATED,
        data=WebsiteMapper.to_response(website),
    )

@router.delete("/{website_id}/delete", response_model=SuccessResponse[None])
async def delete_website(website_id: str, service: HTTP_monitorService = Depends(get_website_service)):
    await service.delete_website(website_id)

    return success_response(
        message=Messages.WEBSITE_DELETED,
        data=None,
    )

@router.patch("/{website_id}/activate", response_model=SuccessResponse[WebsiteResponse])
async def activate_website(website_id: str, service: HTTP_monitorService = Depends(get_website_service)):
    website = await service.activate_website(website_id)

    return success_response(
        message=Messages.WEBSITE_ACTIVATED,
        data=WebsiteMapper.to_response(website),
    )

@router.patch("/{website_id}/deactivate", response_model=SuccessResponse[WebsiteResponse])
async def deactivate_website(website_id: str, service: HTTP_monitorService = Depends(get_website_service)):
    website = await service.deactivate_website(website_id)

    return success_response(
        message=Messages.WEBSITE_DEACTIVATED,
        data=WebsiteMapper.to_response(website),
    )

