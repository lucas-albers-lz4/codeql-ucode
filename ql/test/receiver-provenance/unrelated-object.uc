import { popen } from 'fs';
function read(x) { return x; }
function close() {}
function unrelated() {
  const fd = { read: read, close: close };
  fd.read('all');
  fd.close();
}
