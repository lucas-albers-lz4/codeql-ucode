import { popen } from 'fs';
const methods = {
  probe: {
    call: function(payload) {
      return popen(`echo " ${payload.args.value} " done`);
    }
  }
};
return { probe: methods };
