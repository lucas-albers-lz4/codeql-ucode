import { popen } from 'fs';
const methods = {
  probe: {
    call: function(payload) {
      payload = { args: { value: 'constant' } };
      return popen(`echo ${payload.args.value} done`);
    }
  }
};
return { probe: methods };
