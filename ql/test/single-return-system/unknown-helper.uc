const methods = {
  setBlockDetect: { call: function() {
    ensure_permission();
    return { result: system('/bin/true') == 0 };
  } }
};
return { luci: methods };
