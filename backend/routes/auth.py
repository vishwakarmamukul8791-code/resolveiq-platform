from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordRequestForm

from backend.services.logging_service import log_info, log_error
from backend.services.auth_service import (
    authenticate,
    update_last_login,
    create_access_token,
    set_new_password,
    get_current_user
)

router = APIRouter()


@router.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    try:

        user = authenticate(form_data.username, form_data.password)

        if user is None:
            log_info(f"Failed login attempt for username: {form_data.username}")
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password."
            )

        update_last_login(form_data.username)

        token = create_access_token(form_data.username)

        log_info(f"Successful login: {form_data.username}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "must_reset_password": user["must_reset_password"]
        }

    except HTTPException:
        raise

    except RuntimeError as e:
        log_error(f"Login misconfigured: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        log_error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed.")


@router.post("/auth/reset-password")
def reset_password(
    new_password: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    try:

        if len(new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters."
            )

        set_new_password(current_user, new_password)

        log_info(f"Password reset for user: {current_user}")

        return {
            "message": "Password updated successfully.",
            "must_reset_password": False
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        log_error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed.")