from fastapi import APIRouter
import sys

sys.path.append("./models")
from consultar_estudiante import consultar_estudiante
from schemas.v2 import (
    DifficultyCourseResponse,
    DifficultyPreviewRequest,
    DifficultyPreviewResponse,
    V2PredictionRequest,
    V2PredictionResponse,
)


router = APIRouter()


@router.get("/health")
def healthcheck():
    return {
        "status": "ok",
        "version": "current",
    }


@router.get("/consultar_estudiante/{estudiante_id}")
def consultar_estudiante_v2(estudiante_id: str):
    return consultar_estudiante(estudiante_id)


@router.post("/preview-difficulty", response_model=DifficultyPreviewResponse)
def preview_difficulty(request: DifficultyPreviewRequest):
    from services.v2_features import get_v2_feature_service

    service = get_v2_feature_service()
    feature_bundle = service.build_feature_vector(
        student_id=request.estudiante_id,
        course_codes=request.cursos,
        period=request.periodo,
    )

    difficulty_courses = feature_bundle["difficulty_courses"]
    feature_values = feature_bundle["feature_values"]

    return DifficultyPreviewResponse(
        estudiante_id=request.estudiante_id,
        periodo=feature_bundle["period"],
        total_courses=len(feature_bundle["course_selection"]),
        total_credits=float(sum(course["credits"] for course in difficulty_courses)),
        course_selection=feature_bundle["course_selection"],
        difficulty_courses=[
            DifficultyCourseResponse(**course)
            for course in difficulty_courses
        ],
        semester_aggregates={
            "DIFF_MEAN_WEIGHTED": float(feature_values["DIFF_MEAN_WEIGHTED"]),
            "DIFF_MIN": float(feature_values["DIFF_MIN"]),
            "DIFF_STD": float(feature_values["DIFF_STD"]),
        },
        difficulty_level_legend=feature_bundle["difficulty_level_legend"],
        historical_combination_summary=feature_bundle["historical_combination_summary"],
    )


@router.post("/predecir", response_model=V2PredictionResponse)
def predecir_v2(request: V2PredictionRequest):
    from services.v2_features import get_v2_feature_service
    from services.v2_model import get_v2_prediction_service

    feature_service = get_v2_feature_service()
    prediction_service = get_v2_prediction_service()

    base_feature_overrides = {
        key: value
        for key, value in {
            "pga_anterior": request.pga_anterior,
            "semestres_anteriores": request.semestres_anteriores,
            "pct_creditos_anterior": request.pct_creditos_anterior,
        }.items()
        if value is not None
    }

    feature_bundle = feature_service.build_feature_vector(
        student_id=request.estudiante_id,
        course_codes=request.cursos,
        period=request.periodo,
        total_credits=request.creditos,
        base_feature_overrides=base_feature_overrides,
    )

    prediction = prediction_service.predict_from_feature_values(feature_bundle["feature_values"])
    difficulty_courses = feature_bundle["difficulty_courses"]
    hardest_course = min(difficulty_courses, key=lambda course: course["difficulty_rate"])
    risk_label = "riesgo" if prediction["at_risk"] else "no_riesgo"

    return V2PredictionResponse(
        estudiante_id=request.estudiante_id,
        periodo=feature_bundle["period"],
        model_version=prediction["model_version"],
        score=prediction["score"],
        at_risk=prediction["at_risk"],
        threshold=prediction["threshold"],
        score_p10=prediction.get("score_p10"),
        score_p90=prediction.get("score_p90"),
        score_std=prediction.get("score_std"),
        score_iqr=prediction.get("score_iqr"),
        confidence_level=prediction.get("confidence_level"),
        neighbor_count=prediction.get("neighbor_count"),
        feature_values={
            key: float(value)
            for key, value in feature_bundle["feature_values"].items()
        },
        course_selection=feature_bundle["course_selection"],
        difficulty_courses=[
            DifficultyCourseResponse(**course)
            for course in difficulty_courses
        ],
        difficulty_sources={
            str(course["course_code"]): str(course["source_level"])
            for course in difficulty_courses
        },
        difficulty_level_legend=feature_bundle["difficulty_level_legend"],
        historical_combination_summary=feature_bundle["historical_combination_summary"],
        summary={
            "risk_label": risk_label,
            "message": (
                "Predicción de riesgo activada"
                if prediction["at_risk"]
                else "Predicción de exito esperada"
            ),
            "total_courses": len(feature_bundle["course_selection"]),
            "total_credits": float(
                request.creditos
                if request.creditos is not None
                else sum(course["credits"] for course in difficulty_courses)
            ),
            "hardest_course": str(hardest_course["course_code"]),
            "hardest_course_difficulty": float(hardest_course["difficulty_rate"]),
            "difficulty_mean_weighted": float(feature_bundle["feature_values"]["DIFF_MEAN_WEIGHTED"]),
            "difficulty_min": float(feature_bundle["feature_values"]["DIFF_MIN"]),
            "difficulty_std": float(feature_bundle["feature_values"]["DIFF_STD"]),
        },
    )
