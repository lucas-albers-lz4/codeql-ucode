import { fd } from 'other';
function imported_receiver() {
  fd.read('all');
  fd.close();
}
