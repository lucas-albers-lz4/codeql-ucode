import { popen } from 'fs';
const methods = {
  probe: {
    call: function(payload) {
      let seen = payload.args.value;
      return popen(`echo constant done`);
    }
  }
};
return { probe: methods };
