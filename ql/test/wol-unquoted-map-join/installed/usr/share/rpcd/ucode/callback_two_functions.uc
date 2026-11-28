import { popen } from 'fs';
function transform(s) { return s; }
function transform(s) { return 'constant'; }
const methods = {
  exec: {
    call: function(request) {
      let parts = map(request.args.args, transform);
      const fd = popen('/bin/echo' + ' ' + join(' ', parts));
      return fd;
    }
  }
};
return { 'testing.wol': methods };
