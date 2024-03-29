# -*- coding: utf-8 -*-
from marvinbot.utils import localized_date, get_message, trim_markdown
from marvinbot.handlers import CommonFilters, CommandHandler, MessageHandler
from marvinbot.filters import RegexpFilter, MultiRegexpFilter
from marvinbot_factoids_plugin.models import Factoid
from marvinbot.signals import plugin_reload
from marvinbot.plugins import Plugin
from marvinbot.models import User

import logging
import re
import threading

log = logging.getLogger(__name__)

FACTOID_PATTERNS = [
    r'^(?P<subject>(?:\s?[\w\u00C0-\u017F]+){,5}|[#@]\w+)\s+(?P<verb>is|es|est[aá]?|son|eran?|ser[aá]n|somos|[eé]ramos|seremos|ser[íi]an?|ser[íi]amos|fue|fueron|fuisteis)\s+(?P<predicate>[^\?]*)(?<![\?])$'
]

QUESTION_PATTERNS = [
    r'^(?:(?:(?:y|entonces)\s+)?(?:qu|kh?)[ée]\s(?:es?|eran?|son)\s+)?(?P<subject>(?:\s?[\w\u00C0-\u017F]+){,5}|[#@]\w+)\?+'
]

# TODO: This should come from mongo!
DISABLED_SUBJECTS = [
    'por que', 'why', 'si', 'eso', 'que', 'no', 'cual', 'quien', 'donde', 'cuando',
    'porque'
]


class FactoidsPlugin(Plugin):
    def __init__(self):
        super(FactoidsPlugin, self).__init__('factoids')
        self.bot = None
        self.config = None
        self.factoid_patterns = []
        self.question_patterns = []

    def get_default_config(self):
        return {
            'short_name': self.name,
            'enabled': True,
            'answer_format': '💬 *{username}* ha dicho que *{subject}* {verb} {predicate}'
        }

    def configure(self, config):
        self.config = config
        for pattern in FACTOID_PATTERNS:
            self.factoid_patterns.append(re.compile(pattern, flags=re.IGNORECASE))
        for pattern in QUESTION_PATTERNS:
            self.question_patterns.append(re.compile(pattern, flags=re.IGNORECASE))

    def setup_handlers(self, adapter):
        self.bot = adapter.bot
        self.add_handler(MessageHandler([RegexpFilter(FACTOID_PATTERNS[0]), RegexpFilter(QUESTION_PATTERNS[0])], self.on_text, False), priority=80)

    def setup_schedules(self, adapter):
        pass

    @classmethod
    def fetch_factoid(cls, chat_id, subject):
        try:
            return Factoid.by_chat_id_and_subject(chat_id, subject)
        except:
            return None

    @classmethod
    def add_factoid(cls, **kwargs):
        try:
            factoid = Factoid(**kwargs)
            factoid.save()
            return True
        except Exception as err:
            log.info(err)
            return False

    @classmethod
    def remove_factoid(cls, chat_id, subject):
        factoid = FactoidsPlugin.fetch_factoid(chat_id, subject)
        if factoid and factoid.date_deleted is None:
            factoid.date_deleted = localized_date()
            factoid.save()
            return True
        return False

    def on_text(self, update, **kwargs):
        message = update.effective_message
        text = message.text
        if len(text) == 0:
            return

        def handle_factoid_match(m):
            chat_id = message.chat_id
            subject = trim_markdown(m.group('subject'))
            if subject.lower() in DISABLED_SUBJECTS:
                return
            verb = trim_markdown(m.group('verb'))
            predicate = trim_markdown(m.group('predicate'))
            user_id = message.from_user.id
            username = message.from_user.username
            date_added = localized_date()
            date_modified = localized_date()

            payload = {
                'chat_id': chat_id,
                'subject': subject,
                'verb': verb,
                'predicate': predicate,
                'user_id': user_id,
                'username': username,
                'date_added': date_added,
                'date_modified': date_modified,
            }

            factoid = FactoidsPlugin.fetch_factoid(chat_id, subject)
            if factoid:
                payload['id'] = factoid.id

            FactoidsPlugin.add_factoid(**payload)

        def handle_question_match(m):
            chat_id = message.chat_id
            subject = m.group('subject')
            if subject.lower() in DISABLED_SUBJECTS:
                return
            factoid = FactoidsPlugin.fetch_factoid(chat_id, subject)
            if factoid is None or factoid.date_deleted is not None:
                return
            unknown_username = self.config.get('unknown_username')
            answer_format = self.config.get('answer_format')
            username = factoid.username if factoid.username else unknown_username
            verb = factoid.verb
            predicate = factoid.predicate
            response = answer_format.format(username=username,
                                            subject=subject,
                                            verb=verb,
                                            predicate=predicate)
            self.bot.sendMessage(chat_id=chat_id, text=response,
                                 parse_mode='Markdown')

        for pattern in self.factoid_patterns:
            m = pattern.match(text)
            if m:
                handle_factoid_match(m)
                return

        for pattern in self.question_patterns:
            m = pattern.match(text)
            if m:
                handle_question_match(m)
                return
