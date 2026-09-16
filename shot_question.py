#!/usr/bin/env python3
"""One extra artifact: the question entry with the honest CONCEPT response card."""
import time
from capture import Tab, MEDIA, URL

tab = Tab()
tab.goto(URL)
tab.eval("""(() => {
  document.documentElement.style.scrollBehavior = 'auto';
  const i = document.getElementById('ask-input');
  i.value = 'who should a mind beyond ours answer to?';
  document.getElementById('ask-form').requestSubmit();
})()""")
time.sleep(0.5)
tab.eval("document.querySelector('.ask').scrollIntoView({block:'start'});"
         "window.scrollBy(0,-30)")
time.sleep(0.5)
tab.shot(MEDIA / "hero-question-entry.png")
tab.close()
print("done")
