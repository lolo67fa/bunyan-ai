import { useEffect, useRef, useState } from 'react';
import { useToast } from '../components/ui.jsx';
import { getPrefs, savePrefs } from '../lib/prefs.js';

const FAQ = [
  ['ما هو تطبيق CRUD؟', 'تطبيق يدير قائمة من نوع واحد: منتجات أو مهام أو مواعيد، ويتيح أربع عمليات: الإضافة (Create)، والعرض (Read)، والتعديل (Update)، والحذف (Delete).'],
  ['ما الذي يستطيع بُنيان بناءه؟', 'مواقع ويب بسيطة لكيان واحد، مع بحث وترتيب وتحقق من الحقول، بالعربية أو الإنجليزية. لا يبني حالياً تطبيقات جوال أو ألعاباً، ولا أنظمة فيها دفع أو تسجيل دخول أو قاعدة بيانات خارجية.'],
  ['كيف يعمل الوكلاء معاً؟', 'يكتب محلّل الأعمال المتطلبات، ثم يصمم المهندس الهيكل، ويكتب المطوّر الكود، ويفحصه مختبر الجودة، وأخيراً يلخّص مدير المشروع الخطة والمخاطر. كل وكيل يعمل على مخرجات الذي قبله.'],
  ['لماذا يسألني المحلّل أسئلة؟', 'الوصف القصير يحتمل أكثر من معنى. الإجابة عن سؤالين أو ثلاثة الآن توفّر تطبيقاً لا يناسبك لاحقاً.'],
  ['لماذا الموافقة على المتطلبات مهمة؟', 'كل ما يأتي بعدها يعتمد عليها، ولا يبدأ البناء قبلها. إذا لم تكن مناسبة اطلب تعديلاً وسيعيد المحلّل كتابتها.'],
  ['ماذا تعني نتائج الاختبار؟', 'يشغّل مختبر الجودة ثمانية فحوصات على التطبيق في متصفح حقيقي. إذا فشل فحص يصلحه المطوّر، بحد أقصى محاولتان، ثم تُعاد الفحوصات كلها.'],
  ['كيف أفتح تطبيقي؟', 'حمّل ملف ZIP وفك ضغطه، ثم افتح index.html في المتصفح.'],
];

export default function SettingsPage({ focusHelp }) {
  const [prefs, setPrefs] = useState(getPrefs);
  const toast = useToast();
  const helpRef = useRef(null);

  useEffect(() => {
    if (focusHelp) helpRef.current?.scrollIntoView({ block: 'start' });
  }, [focusHelp]);

  return (
    <div className="page page-narrow" data-testid="settings-page">
      <section style={{ display: 'grid', gap: 'var(--bn-s2)' }}>
        <h1 className="title">الإعدادات</h1>
        <p className="muted small">تفضيلات العرض على هذا الجهاز.</p>
        <form onSubmit={(e) => { e.preventDefault(); savePrefs(prefs); toast('حُفظت الإعدادات.'); }}>
          <div className="setting">
            <div>
              <div className="field-label">لغة الواجهة</div>
              <p className="muted small">لغة التطبيق الناتج تُحدَّد لكل مشروع من فكرتك.</p>
            </div>
            <div className="inline-choices">
              <label className="choice"><input type="radio" name="lang" defaultChecked /> العربية</label>
              <label className="choice muted"><input type="radio" name="lang" disabled /> English (قريباً)</label>
            </div>
          </div>
          <div className="setting">
            <div className="field-label">المظهر</div>
            <div className="inline-choices" role="radiogroup">
              {[['light', 'فاتح'], ['dark', 'داكن'], ['system', 'حسب الجهاز']].map(([v, l]) => (
                <label key={v} className="choice">
                  <input type="radio" name="theme" value={v} checked={prefs.theme === v} onChange={() => setPrefs({ ...prefs, theme: v })} data-testid={`theme-${v}`} />
                  {l}
                </label>
              ))}
            </div>
          </div>
          <div className="setting">
            <div className="field-label">الحركة</div>
            <label className="choice">
              <input type="checkbox" checked={prefs.reduceMotion} onChange={(e) => setPrefs({ ...prefs, reduceMotion: e.target.checked })} />
              تقليل الحركة في الواجهة
            </label>
          </div>
          <div style={{ paddingTop: 'var(--bn-s4)' }}>
            <button className="btn btn-primary" data-testid="save-settings">حفظ</button>
          </div>
        </form>
      </section>

      <section ref={helpRef} className="section" id="help" style={{ marginTop: 'var(--bn-s5)' }}>
        <h2 className="title">كيف يعمل بُنيان؟</h2>
        <p className="muted small">إجابات مختصرة قبل مشروعك الأول.</p>
        <div className="faq">
          {FAQ.map(([q, a]) => (
            <div key={q}>
              <h3>{q}</h3>
              <p>{a}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
