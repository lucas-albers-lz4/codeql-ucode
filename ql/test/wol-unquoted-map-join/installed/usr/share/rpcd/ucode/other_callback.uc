import { popen } from 'fs';
function transform(s) { return s; }
const methods = {
  exec: {
    call: function(request) {
      let parts = map(request.args.args, length);
      const fd = popen('/bin/echo' + ' ' + join(' ', parts));
      return fd;
    }
  }
};
return { 'testing.wol': methods };
