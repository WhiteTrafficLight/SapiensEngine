"""
이미지 업로드 및 관리 라우터
- S3 업로드
- 이미지 리사이징/최적화  
- Presigned URL 생성
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
import os
import uuid
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# AWS S3 설정 (환경 변수에서 가져오기)
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'sapiens-engine-assets')

# S3 클라이언트 초기화
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
) if AWS_ACCESS_KEY and AWS_SECRET_KEY else None

class UploadResponse(BaseModel):
    success: bool
    message: str
    urls: Optional[dict] = None
    file_id: Optional[str] = None

class PresignedUrlRequest(BaseModel):
    file_type: str
    file_size: int
    folder: str  # users/profiles, npcs/custom, etc.

def validate_image_file(file: UploadFile) -> bool:
    """이미지 파일 검증"""
    # 파일 타입 체크
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        return False
    
    # 파일 크기 체크 (10MB)
    max_size = 10 * 1024 * 1024
    if hasattr(file.file, 'seek'):
        file.file.seek(0, 2)  # 파일 끝으로 이동
        size = file.file.tell()
        file.file.seek(0)  # 다시 처음으로
        if size > max_size:
            return False
    
    return True

def resize_image(image_data: bytes, size: tuple, quality: int = 85) -> bytes:
    """이미지 리사이징"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # RGBA to RGB 변환 (JPEG 호환성)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # 비율 유지하면서 리사이징
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 중앙 크롭 (정사각형으로)
        if size[0] == size[1]:  # 정사각형인 경우
            width, height = image.size
            if width != height:
                min_side = min(width, height)
                left = (width - min_side) // 2
                top = (height - min_side) // 2
                right = left + min_side
                bottom = top + min_side
                image = image.crop((left, top, right, bottom))
                image = image.resize(size, Image.Resampling.LANCZOS)
        
        # 바이트로 변환
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    
    except Exception as e:
        logger.error(f"Image resize error: {e}")
        raise HTTPException(status_code=400, detail="이미지 처리 중 오류가 발생했습니다.")

@router.post("/presigned-url", response_model=PresignedUrlRequest)
async def get_presigned_url(request: PresignedUrlRequest):
    """S3 Presigned URL 생성 (직접 업로드용)"""
    if not s3_client:
        raise HTTPException(status_code=500, detail="S3가 설정되지 않았습니다.")
    
    try:
        file_id = str(uuid.uuid4())
        file_extension = request.file_type.split('/')[-1]
        if file_extension == 'jpeg':
            file_extension = 'jpg'
        
        key = f"{request.folder}/{file_id}/original.{file_extension}"
        
        # Presigned URL 생성 (15분 유효)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': key,
                'ContentType': request.file_type
            },
            ExpiresIn=900  # 15분
        )
        
        return JSONResponse({
            "success": True,
            "presigned_url": presigned_url,
            "file_id": file_id,
            "key": key
        })
        
    except ClientError as e:
        logger.error(f"S3 presigned URL error: {e}")
        raise HTTPException(status_code=500, detail="Presigned URL 생성 실패")

@router.post("/upload/{category}", response_model=UploadResponse)
async def upload_image(
    category: str,  # userProfile, customNpc, roomThumbnail
    file: UploadFile = File(...),
    user_id: Optional[str] = None
):
    """이미지 업로드 및 처리"""
    if not s3_client:
        raise HTTPException(status_code=500, detail="S3가 설정되지 않았습니다.")
    
    # 파일 검증
    if not validate_image_file(file):
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식이거나 크기가 너무 큽니다.")
    
    try:
        # 파일 읽기
        file_data = await file.read()
        
        # 파일 ID 생성
        file_id = user_id or str(uuid.uuid4())
        
        # 카테고리별 폴더 설정
        folder_map = {
            'userProfile': 'users/profiles',
            'customNpc': 'npcs/custom', 
            'roomThumbnail': 'rooms/thumbnails'
        }
        
        if category not in folder_map:
            raise HTTPException(status_code=400, detail="지원하지 않는 카테고리입니다.")
        
        folder = folder_map[category]
        urls = {}
        
        # 원본 이미지 업로드
        original_key = f"{folder}/{file_id}/original.jpg"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=original_key,
            Body=file_data,
            ContentType='image/jpeg'
        )
        urls['original'] = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{original_key}"
        
        # 썸네일 생성 및 업로드
        if category in ['userProfile', 'customNpc']:
            thumbnail_data = resize_image(file_data, (100, 100), quality=80)
            thumbnail_key = f"{folder}/{file_id}/thumbnail.jpg"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=thumbnail_key,
                Body=thumbnail_data,
                ContentType='image/jpeg'
            )
            urls['thumbnail'] = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{thumbnail_key}"
        
        # 포트레이트 생성 (Custom NPC용)
        if category == 'customNpc':
            portrait_data = resize_image(file_data, (400, 400), quality=85)
            portrait_key = f"{folder}/{file_id}/portrait.jpg"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=portrait_key,
                Body=portrait_data,
                ContentType='image/jpeg'
            )
            urls['portrait'] = portrait_key
        
        logger.info(f"Image uploaded successfully: {file_id} in {category}")
        
        return UploadResponse(
            success=True,
            message="이미지가 성공적으로 업로드되었습니다.",
            urls=urls,
            file_id=file_id
        )
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="이미지 업로드 실패")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="업로드 처리 중 오류가 발생했습니다.")

@router.delete("/delete/{category}/{file_id}")
async def delete_image(category: str, file_id: str):
    """이미지 삭제"""
    if not s3_client:
        raise HTTPException(status_code=500, detail="S3가 설정되지 않았습니다.")
    
    folder_map = {
        'userProfile': 'users/profiles',
        'customNpc': 'npcs/custom',
        'roomThumbnail': 'rooms/thumbnails'
    }
    
    if category not in folder_map:
        raise HTTPException(status_code=400, detail="지원하지 않는 카테고리입니다.")
    
    try:
        folder = folder_map[category]
        
        # 해당 폴더의 모든 파일 삭제
        prefix = f"{folder}/{file_id}/"
        objects = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        
        if 'Contents' in objects:
            delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
            s3_client.delete_objects(
                Bucket=S3_BUCKET,
                Delete={'Objects': delete_keys}
            )
        
        logger.info(f"Images deleted successfully: {file_id} in {category}")
        
        return JSONResponse({
            "success": True,
            "message": "이미지가 성공적으로 삭제되었습니다."
        })
        
    except ClientError as e:
        logger.error(f"S3 delete error: {e}")
        raise HTTPException(status_code=500, detail="이미지 삭제 실패")

@router.get("/health")
async def upload_health():
    """업로드 서비스 상태 확인"""
    s3_status = "connected" if s3_client else "not_configured"
    
    return {
        "status": "healthy",
        "s3_status": s3_status,
        "bucket": S3_BUCKET if s3_client else None
    } 