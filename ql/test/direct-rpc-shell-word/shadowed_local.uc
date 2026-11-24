import { popen } from 'fs';
const methods = {
  probe: {
    call: function(payload) {
      let cmd;
      cmd = `echo ${payload.args.value} done`;
      {
        let cmd = `echo constant done`;
        return popen(cmd);
      }
    }
  }
};
return { probe: methods };
