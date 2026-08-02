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
from backend.services.session_service import create_session, close_session

router = APIRouter()


@router.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate(form_data.username, form_data.password)

        if user is None:
            log_info(f"Failed login attempt: {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        update_last_login(form_data.username)
        session_id = create_session(form_data.username)
        token = create_access_token(form_data.username, user["role"])

        log_info(f"Login: {form_data.username} role={user['role']} session={session_id[:8]}")

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user["role"],
            "username": form_data.username,
            "session_id": session_id,
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


@router.post("/auth/logout")
def logout(
    session_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        close_session(
            session_id,
            current_user["username"],
        )
        log_info(f"Logout: {current_user['username']} session={session_id[:8]}")
        return {"message": "Logged out successfully."}
    except Exception as e:
        log_error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout failed.")


@router.post("/auth/reset-password")
def reset_password(
    new_password: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")

        set_new_password(current_user["username"], new_password)
        log_info(f"Password reset: {current_user['username']}")

        return {"message": "Password updated successfully.", "must_reset_password": False}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error(f"Password reset failed: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed.")


@router.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "must_reset_password": current_user["must_reset_password"],
    }
