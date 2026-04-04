"""
HTML-Mail-Template im Design der BabyApp.
Wird für alle ausgehenden Mails verwendet.
"""


def render_mail(titel, inhalt, button_text=None, button_url=None, footer_text=None):
    """
    Erzeugt eine gestylte HTML-Mail.

    :param titel: Überschrift der Mail
    :param inhalt: HTML-Inhalt (Paragraphen etc.)
    :param button_text: Optionaler Button-Text
    :param button_url: Optionale Button-URL
    :param footer_text: Optionaler Footer-Text
    """
    button_html = ''
    if button_text and button_url:
        button_html = f'''
        <tr><td style="padding:24px 0 8px;">
            <a href="{button_url}" style="display:inline-block;padding:12px 28px;background:#5d7a54;color:#ffffff;
               text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;font-family:Nunito,Arial,sans-serif;">
                {button_text}
            </a>
        </td></tr>
        <tr><td style="padding:4px 0 16px;">
            <span style="font-size:12px;color:#8a7e6a;">Oder kopiere diesen Link:</span><br>
            <a href="{button_url}" style="font-size:12px;color:#5d7a54;word-break:break-all;">{button_url}</a>
        </td></tr>
        '''

    footer = footer_text or 'Diese E-Mail wurde automatisch von der BabyApp gesendet.'

    return f'''<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f1ec;font-family:Nunito,Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f1ec;padding:32px 16px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#fffcf8;border-radius:12px;
       border:1px solid #ddd5ca;overflow:hidden;">

    <!-- Header -->
    <tr><td style="background:#3b3028;padding:20px 24px;text-align:center;">
        <table cellpadding="0" cellspacing="0" style="margin:0 auto;"><tr>
            <td style="width:36px;height:36px;background:#5d7a54;border-radius:8px;text-align:center;vertical-align:middle;">
                <span style="color:#fff;font-size:18px;font-weight:800;line-height:36px;">B</span>
            </td>
            <td style="padding-left:10px;color:#f0ebe5;font-size:18px;font-weight:800;letter-spacing:-0.5px;">
                BabyApp
            </td>
        </tr></table>
    </td></tr>

    <!-- Inhalt -->
    <tr><td style="padding:28px 28px 12px;">
        <h1 style="margin:0 0 16px;color:#3b3028;font-size:20px;font-weight:800;font-family:Nunito,Arial,sans-serif;">
            {titel}
        </h1>
        <div style="color:#3b3028;font-size:15px;line-height:1.6;font-family:Nunito,Arial,sans-serif;">
            {inhalt}
        </div>
    </td></tr>

    <!-- Button -->
    <tr><td style="padding:0 28px;text-align:center;">
        <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
        {button_html}
        </table>
    </td></tr>

    <!-- Footer -->
    <tr><td style="padding:20px 28px;border-top:1px solid #ddd5ca;text-align:center;">
        <span style="font-size:12px;color:#8a7e6a;font-family:Nunito,Arial,sans-serif;">
            {footer}
        </span>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''
