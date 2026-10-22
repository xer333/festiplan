from app.domain.events import ConcertRescheduled, PlanningPublished, PlanningUnpublished
from app.utils.email_sender import send_email


class EmailNotifier:
    def notify(self, event):
        if isinstance(event, ConcertRescheduled):
            subject = f'Modification du concert #{event.concert_id}'
            message = f'Concert déplacé au {event.slot.start.isoformat()}'
        elif isinstance(event, PlanningPublished):
            subject = f'Publication du festival #{event.festival_id}'
            message = 'Le planning a été publié.'
        elif isinstance(event, PlanningUnpublished):
            subject = f'Dépublication du festival #{event.festival_id}'
            message = 'Le planning est à nouveau en préparation.'
        else:
            raise TypeError(f'Événement inconnu : {type(event)}')
        send_email('production@festiplan.test', subject, message)
