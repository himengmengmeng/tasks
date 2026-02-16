"""
Chat API endpoints for AI Agent conversations.
Supports conversation CRUD and SSE streaming for chat messages.
"""
import json
import logging
import asyncio
from typing import TYPE_CHECKING, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist

from .auth import get_current_active_user

if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Models ====================

class ConversationCreate(BaseModel):
    name: Optional[str] = ""

class ConversationUpdate(BaseModel):
    name: str

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    tool_calls: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True

class ConversationDetailResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


# ==================== Helper Functions ====================

async def _get_conversation(conversation_id: int, user):
    """Get a conversation owned by the user."""
    from ai_chat.models import Conversation
    try:
        return await sync_to_async(
            Conversation.objects.get
        )(id=conversation_id, creator=user)
    except Conversation.DoesNotExist:
        raise HTTPException(status_code=404, detail="Conversation not found")


# ==================== Endpoints ====================

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user)
) -> ConversationResponse:
    """Create a new conversation."""
    from ai_chat.models import Conversation

    conversation = await sync_to_async(Conversation.objects.create)(
        name=data.name or "",
        creator=current_user
    )
    return ConversationResponse(
        id=conversation.id,
        name=conversation.name,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
) -> ConversationListResponse:
    """List all conversations for the current user."""
    from ai_chat.models import Conversation
    from django.db.models import Count

    queryset = Conversation.objects.filter(creator=current_user).annotate(
        msg_count=Count('messages')
    )
    total = await sync_to_async(queryset.count)()
    conversations = await sync_to_async(list)(
        queryset.order_by('-updated_at')[skip:skip + limit]
    )

    results = [
        ConversationResponse(
            id=c.id,
            name=c.name,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=c.msg_count
        )
        for c in conversations
    ]

    return ConversationListResponse(conversations=results, total=total)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user)
) -> ConversationDetailResponse:
    """Get a conversation with all its messages."""
    from ai_chat.models import Conversation, Message

    conversation = await _get_conversation(conversation_id, current_user)

    messages = await sync_to_async(list)(
        Message.objects.filter(conversation=conversation).order_by('created_at')
    )

    message_responses = [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            created_at=m.created_at
        )
        for m in messages
    ]

    return ConversationDetailResponse(
        id=conversation.id,
        name=conversation.name,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_responses
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user)
) -> ConversationResponse:
    """Update a conversation's name."""
    from ai_chat.models import Message

    conversation = await _get_conversation(conversation_id, current_user)
    conversation.name = data.name
    await sync_to_async(conversation.save)()

    msg_count = await sync_to_async(
        Message.objects.filter(conversation=conversation).count
    )()

    return ConversationResponse(
        id=conversation.id,
        name=conversation.name,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a conversation and all its messages."""
    conversation = await _get_conversation(conversation_id, current_user)
    await sync_to_async(conversation.delete)()
    return None


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a message and get AI response via Server-Sent Events (SSE).
    
    SSE Event types:
    - event: token     -> data: {"content": "partial text"}
    - event: tool_call -> data: {"name": "tool_name", "args": {...}}
    - event: tool_result -> data: {"name": "tool_name", "result": "..."}
    - event: done      -> data: {"message_id": 123, "conversation_name": "..."}
    - event: error     -> data: {"detail": "error message"}
    """
    from ai_chat.models import Conversation, Message
    from api.agent.graph import stream_agent_response, generate_conversation_name

    conversation = await _get_conversation(conversation_id, current_user)

    # Save the human message
    human_msg = await sync_to_async(Message.objects.create)(
        conversation=conversation,
        role="human",
        content=data.content
    )

    # Load conversation history
    existing_messages = await sync_to_async(list)(
        Message.objects.filter(conversation=conversation)
        .order_by('created_at')
        .values('role', 'content')
    )
    history = [{"role": m["role"], "content": m["content"]} for m in existing_messages[:-1]]

    async def event_generator():
        full_content = ""
        tool_calls_data = None

        try:
            async for event in stream_agent_response(
                user_id=current_user.id,
                user_message=data.content,
                history=history,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    full_content += event["content"]
                    yield f"event: token\ndata: {json.dumps({'content': event['content']})}\n\n"

                elif event_type == "tool_call":
                    yield f"event: tool_call\ndata: {json.dumps({'name': event['name'], 'args': event['args']}, default=str)}\n\n"

                elif event_type == "tool_result":
                    yield f"event: tool_result\ndata: {json.dumps({'name': event['name'], 'result': event['result']}, default=str)}\n\n"

                elif event_type == "done":
                    full_content = event.get("full_content", full_content)
                    tool_calls_data = event.get("tool_calls_data")

                elif event_type == "error":
                    yield f"event: error\ndata: {json.dumps({'detail': event['detail']})}\n\n"
                    return

            # Save AI message to database
            if full_content:
                ai_msg = await sync_to_async(Message.objects.create)(
                    conversation=conversation,
                    role="ai",
                    content=full_content,
                    tool_calls=tool_calls_data
                )

                # Update conversation timestamp
                await sync_to_async(conversation.save)()

                # Auto-name the conversation after first exchange
                conversation_name = conversation.name
                if not conversation.name:
                    all_messages = await sync_to_async(list)(
                        Message.objects.filter(conversation=conversation)
                        .order_by('created_at')
                        .values('role', 'content')
                    )
                    msg_list = [{"role": m["role"], "content": m["content"]} for m in all_messages]
                    conversation_name = await generate_conversation_name(msg_list)
                    conversation.name = conversation_name
                    await sync_to_async(conversation.save)(update_fields=['name'])

                yield f"event: done\ndata: {json.dumps({'message_id': ai_msg.id, 'conversation_name': conversation_name})}\n\n"
            else:
                yield f"event: done\ndata: {json.dumps({'message_id': None, 'conversation_name': conversation.name})}\n\n"

        except Exception as e:
            logger.error(f"SSE streaming error: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
