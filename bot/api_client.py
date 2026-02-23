import requests
from typing import Optional, Dict, List


class TaskPilotAPI:
    """HTTP client for communicating with TaskPilot web service"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def link_telegram_account(self, code: str, telegram_id: int, telegram_username: str) -> Dict:
        """Link Telegram account using the linking code"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/telegram/link",
                json={
                    'code': code,
                    'telegram_id': telegram_id,
                    'telegram_username': telegram_username
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {'error': str(e)}

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Get user info by Telegram ID"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/telegram/user/{telegram_id}"
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def get_user_tasks(
        self,
        telegram_id: int,
        status: Optional[str] = None,
        project_id: Optional[int] = None,
        assignee_id: Optional[int] = None
    ) -> Dict:
        """Get tasks visible to user with optional filters

        For managers: returns all tenant tasks
        For members: returns only assigned tasks
        """
        try:
            params = {'telegram_id': telegram_id}
            if status:
                params['status'] = status
            if project_id:
                params['project_id'] = project_id
            if assignee_id:
                params['assignee_id'] = assignee_id

            response = self.session.get(
                f"{self.base_url}/api/telegram/tasks",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {'tasks': [], 'is_manager': False}

    def get_task_details(self, telegram_id: int, task_id: int) -> Optional[Dict]:
        """Get detailed task information"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/telegram/tasks/{task_id}",
                params={'telegram_id': telegram_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def create_task(
        self,
        telegram_id: int,
        title: str,
        project_id: int,
        priority: str,
        description: str = '',
        assignee_id: Optional[int] = None,
        due_date: Optional[str] = None,
    ) -> Dict:
        """Create a new task"""
        try:
            payload = {
                'telegram_id': telegram_id,
                'title': title,
                'project_id': project_id,
                'priority': priority,
            }
            if description:
                payload['description'] = description
            if assignee_id is not None:
                payload['assignee_id'] = assignee_id
            if due_date:
                payload['due_date'] = due_date

            response = self.session.post(
                f"{self.base_url}/api/telegram/tasks",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {'error': str(e)}

    def update_task_status(self, telegram_id: int, task_id: int, new_status: str) -> Dict:
        """Update task status"""
        try:
            response = self.session.patch(
                f"{self.base_url}/api/telegram/tasks/{task_id}/status",
                json={
                    'telegram_id': telegram_id,
                    'status': new_status
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {'error': str(e)}

    def get_tenant_members(self, telegram_id: int) -> List[Dict]:
        """Get tenant members for assignee selection"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/telegram/members",
                params={'telegram_id': telegram_id}
            )
            response.raise_for_status()
            return response.json().get('members', [])
        except requests.RequestException:
            return []

    def get_user_projects(self, telegram_id: int) -> List[Dict]:
        """Get projects available to user"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/telegram/projects",
                params={'telegram_id': telegram_id}
            )
            response.raise_for_status()
            return response.json().get('projects', [])
        except requests.RequestException:
            return []

    def get_tenant_settings(self, telegram_id: int) -> Optional[Dict]:
        """Get tenant settings for AI features"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/telegram/settings",
                params={'telegram_id': telegram_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def improve_text_with_ai(self, telegram_id: int, text: str, mode: str = 'fix') -> Optional[str]:
        """Improve text using tenant's AI settings

        Args:
            telegram_id: User's Telegram ID
            text: Text to improve
            mode: 'fix' for fixing language or 'translate' for translation

        Returns:
            Improved text or None on error
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Get tenant settings first
            settings = self.get_tenant_settings(telegram_id)
            logger.info(f"Tenant settings for {telegram_id}: {settings}")

            if not settings:
                logger.warning(f"No tenant settings found for {telegram_id}")
                return None

            if not settings.get('ai_enabled'):
                logger.warning(f"AI not enabled for tenant {telegram_id}")
                return None

            # Use the LLM client directly
            from .llm_client import LLMClient
            llm = LLMClient()

            if not llm.is_available():
                logger.warning("LLM client not available (OPENAI_API_KEY missing?)")
                return None

            logger.info(f"Improving text with AI: {text[:50]}...")
            improved_text = llm.improve_task_text(
                text=text,
                system_prompt=settings.get('ai_system_prompt', ''),
                mode=mode,
                target_language=settings.get('ai_default_language', 'en')
            )

            if improved_text:
                logger.info(f"AI improvement successful: {improved_text[:50]}...")
                return improved_text
            else:
                logger.error("AI improvement returned None")
                return None

        except Exception as e:
            logger.exception(f"Exception in improve_text_with_ai: {e}")
            return None
