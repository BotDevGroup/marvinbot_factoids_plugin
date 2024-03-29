import mongoengine
from marvinbot.utils import localized_date


class Factoid(mongoengine.Document):
    id = mongoengine.SequenceField(primary_key=True)
    chat_id = mongoengine.LongField(required=True)
    subject = mongoengine.StringField(required=True)
    verb = mongoengine.StringField(required=True)
    predicate = mongoengine.StringField(required=True)
    user_id = mongoengine.LongField(required=True)
    username = mongoengine.StringField(required=False)

    date_added = mongoengine.DateTimeField(default=localized_date)
    date_modified = mongoengine.DateTimeField(default=localized_date)
    date_deleted = mongoengine.DateTimeField(required=False, null=True)

    @classmethod
    def by_id(cls, id):
        try:
            return cls.objects.get(id=id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def by_chat_id_and_subject(cls, chat_id, subject):
        try:
            return cls.objects.get(chat_id=chat_id, subject__iexact=subject)
        except cls.DoesNotExist:
            return None

    @classmethod
    def all(cls):
        try:
            return cls.objects(date_deleted=None)
        except:
            return None

    def __str__(self):
        return "{{ id = {id}, chat_id = {chat_id} , subject = \"{subject}\", verb = \"{verb}\" , predicate = \"{predicate}\" }}".format(id=self.id, chat_id=self.chat_id, subject=self.subject, verb=self.verb, predicate=self.predicate)
