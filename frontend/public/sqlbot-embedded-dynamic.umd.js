;(function () {
  const resolveBaseUrl = () => {
    const currentScript = document.currentScript
    if (currentScript && currentScript.src) {
      return currentScript.src.replace(/sqlbot-embedded-dynamic\.umd\.js(?:\?.*)?$/, '')
    }
    return window.location.origin + '/'
  }

  const mounted = function (selector, options) {
    const root = document.querySelector(selector)
    if (!root) return

    const embeddedId = options && options.embeddedId ? options.embeddedId : ''
    const iframe = document.createElement('iframe')
    iframe.src = `${resolveBaseUrl()}#/embeddedCommon?id=${embeddedId}`
    iframe.style.width = '100%'
    iframe.style.height = '100%'
    iframe.style.border = '0'

    root.innerHTML = ''
    root.appendChild(iframe)
  }

  window.sqlbot_embedded_handler = window.sqlbot_embedded_handler || {}
  window.sqlbot_embedded_handler.mounted = mounted
})()
