import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      for (let input in [{ args: { value: 'constant' } }])
        return popen(`echo ${input.args.value} done`);
    }
  }
};
return { probe: methods };
