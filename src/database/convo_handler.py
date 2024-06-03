from __init__ import db
from database.database_init import Conversation


class CreateConversation:
    username: str
    model: str
    title: str
    prompt: str
    summary: str = ""
    short_summary: str = ""

    conversation: Conversation

    def __post_init__(self):
        self.conversation = Conversation(
            username=self.username,
            model=self.model,
            title=self.title,
            prompt=self.prompt,
            summary=self.summary,
            short_summary=self.short_summary,
        )
        db.session.add(self.conversation)
        db.session.commit()

    def __repr__(self):
        return f"Conversation created: {self.conversation.id}"ß

    def __str__(self):
        return f"Conversation created: {self.conversation.id}"