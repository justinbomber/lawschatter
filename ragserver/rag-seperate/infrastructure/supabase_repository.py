import logging
from typing import List
from supabase import create_client, ClientOptions
from domain.interfaces import IConversationRepository, Message
from config.settings import Settings

logger = logging.getLogger(__name__)


class SupabaseConversationRepository(IConversationRepository):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.schema = settings.supabase.schema_name
    
    def _create_client_with_token(self, token: str):
        return create_client(
            self.settings.supabase.url,
            self.settings.supabase.key,
            options=ClientOptions(
                headers={
                    "Authorization": f"Bearer {token}"
                },
                schema=self.schema
            )
        )
    
    async def get_conversation_messages(self, token: str, conversation_id: str, limit: int = 10) -> List[Message]:
        client = self._create_client_with_token(token)
        
        response = client.table("messages") \
            .select("message_id, conversation_id, user_id, sender_type, content, created_at") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        messages = []
        for row in reversed(response.data):
            messages.append(Message(
                message_id=row["message_id"],
                conversation_id=row["conversation_id"],
                user_id=row["user_id"],
                sender_type=row["sender_type"],
                content=row["content"],
                created_at=row["created_at"]
            ))
        
        logger.info(f"取得對話 {conversation_id} 的 {len(messages)} 筆歷史訊息")
        return messages
    
    async def verify_user_conversation_access(self, token: str, user_id: str, conversation_id: str) -> bool:
        client = self._create_client_with_token(token)
        
        response = client.table("conversations") \
            .select("conversation_id") \
            .eq("conversation_id", conversation_id) \
            .eq("user_id", user_id) \
            .execute()
        
        has_access = len(response.data) > 0
        
        if not has_access:
            logger.warning(f"使用者 {user_id} 無權訪問對話 {conversation_id}")
        
        return has_access

