import { popen } from 'fs';
function optional_call() {
  const fd = popen('printf harmless');
  fd.read?.('all');
}
