import { type Chain } from 'src/__generated__/graphql/proxy/graphql';
import { NotifyType } from '../notify';
import { useProxyStore } from './store';

const proxy = useProxyStore();

export class Proxy {
  static getMemeApplications = (done?: (error: boolean, rows?: Chain[]) => void) => {
    proxy.getApplications(
      {
        Message: {
          Error: {
            Title: 'Get meme applications',
            Message: 'Failed get meme applications',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      done,
    );
  };

  static tokenCreatorChain = (applicationId: string) => {
    return proxy.chain(applicationId);
  };

  static initialize = () => {
    proxy.initializeProxy();
  };

  static blockHash = () => proxy.blockHash;
}
