import { NotifyType } from './const';
import { type Notification } from './types';
import { Notify } from 'quasar';

const mergeMessage = (notification: Notification) => {
  if (notification.Message) {
    if (notification.Description) {
      return notification.Message + '(' + notification.Description + ')';
    }
    return notification.Message;
  }
  return notification.Description;
};

const success = (notification: Notification): void => {
  Notify.create({
    type: 'positive',
    message: notification.Title as string,
    caption: mergeMessage(notification) as string,
  });
};

const fail = (notification: Notification): void => {
  Notify.create({
    type: 'negative',
    message: notification.Title as string,
    caption: mergeMessage(notification) as string,
  });
};

const warning = (notification: Notification): void => {
  Notify.create({
    type: 'warning',
    message: notification.Title as string,
    caption: mergeMessage(notification) as string,
  });
};

const info = (notification: Notification): void => {
  Notify.create({
    type: 'positive',
    message: notification.Title as string,
    caption: mergeMessage(notification) as string,
  });
};

const notify = (notification: Notification) => {
  if (!notification.Popup) {
    return;
  }
  switch (notification.Type) {
    case NotifyType.Success:
      success(notification);
      break;
    case NotifyType.Error:
      fail(notification);
      break;
    case NotifyType.Info:
      info(notification);
      break;
    case NotifyType.Warning:
      warning(notification);
      break;
    case NotifyType.Waiting:
      return Notify.create({
        type: 'ongoing',
        message: notification.Message as string,
      });
  }
};

export { notify };
