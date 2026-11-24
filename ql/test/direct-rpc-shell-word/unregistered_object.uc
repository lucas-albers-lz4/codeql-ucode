import { popen } from 'fs';
const localUtility = {
  probe: {
    call: function(input) {
      return popen(`echo ${input.args.value} done`);
    }
  }
};
return {};
