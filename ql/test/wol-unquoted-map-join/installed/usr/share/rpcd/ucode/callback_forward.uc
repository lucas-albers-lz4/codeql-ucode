import { popen } from 'fs';
const methods = {
  exec: {
    call: function(request) {
      let parts = map(request.args.args, transform);
      const fd = popen('/bin/echo' + ' ' + join(' ', parts));
      return fd;
    }
  }
};
function transform(s) { return s; }
return { 'testing.wol': methods };
