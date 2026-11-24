import { popen } from 'fs';
const methods = {
  probe: {
    call: function(payload) {
      function inner(payload) {
        return popen(`echo ${payload.args.value} done`);
      }
      return inner({ args: { value: 'constant' } });
    }
  }
};
return { probe: methods };
