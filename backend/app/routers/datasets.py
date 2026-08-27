import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chart, Dataset, User
from app.schemas import DatasetOut, DatasetPreview
from app.security import get_current_user
from app.services.data_service import (
    dataframe_from_bytes,
    dataset_to_out,
    detect_table_kind,
    ensure_upload_dir,
    infer_columns,
    load_dataframe,
    to_preview,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetOut)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    original_name = file.filename or "未命名文件"
    exists = (
        db.query(Dataset)
        .filter(Dataset.owner_id == current.id, Dataset.filename == original_name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"文件「{original_name}」已上传过，请勿重复上传")

    content = await file.read()
    kind = detect_table_kind(content)
    if not kind:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法根据文件内容识别为 CSV / Excel / JSON 表格")

    upload_dir = ensure_upload_dir()
    dest = upload_dir / f"{current.id}_{uuid.uuid4().hex}.{kind}"
    dest.write_bytes(content)

    dataset = Dataset(
        name=name or Path(original_name).stem or "未命名数据集",
        filename=original_name,
        filepath=str(dest),
        source_type="file",
        owner_id=current.id,
    )
    try:
        df = dataframe_from_bytes(content)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}") from exc
    dataset.columns_json = json.dumps(infer_columns(df), ensure_ascii=False)
    dataset.row_count = int(len(df))
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return DatasetOut(**dataset_to_out(dataset))


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    items = (
        db.query(Dataset)
        .filter(Dataset.owner_id == current.id)
        .order_by(Dataset.id.desc())
        .all()
    )
    return [DatasetOut(**dataset_to_out(item)) for item in items]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return DatasetOut(**dataset_to_out(item))


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
def preview_dataset(dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据集不存在")
    df = load_dataframe(item)
    return DatasetPreview(**to_preview(df))


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    item = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.owner_id == current.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据集不存在")
    db.query(Chart).filter(Chart.dataset_id == item.id).delete()
    Path(item.filepath).unlink(missing_ok=True)
    db.delete(item)
    db.commit()
    return {"ok": True}
