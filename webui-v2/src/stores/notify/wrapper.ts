import { notify } from './helper';
import { useNotificationStore } from './store';
import { type Notification } from './types';

const _notify = useNotificationStore();

export class Notify {
  static subscribe = () => {
    _notify.$subscribe((_, state) => {
      state.Notifications.forEach((notif, index) => {
        if (notif.Popup) {
          state.Notifications.splice(index, 1);
          notify(notif);
        }
      });
    });
  };

  static pushNotification = (notification: Notification) => {
    _notify.pushNotification(notification);
  };
}
