# Рукописные пометки

На деку ровно три пометки. Меньше выглядит стерильно, больше превращается в шум.

Ставятся только на три вещи: конфликт, победитель, финальный вопрос.

## Подчёркивание

```html
<svg class="mk mku" viewBox="0 0 600 30" preserveAspectRatio="none">
  <path d="M6 17 C 150 5, 350 27, 594 10" fill="none" stroke="currentColor"
        stroke-width="4" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
</svg>
```

```css
.u   { position: relative; display: inline-block }
.mk  { position: absolute; pointer-events: none }
.mku { left: 0; width: 100%; bottom: -18px; height: 22px }
```

## Обводка овалом

```html
<svg class="mk mkc" viewBox="0 0 300 110" preserveAspectRatio="none">
  <ellipse cx="150" cy="55" rx="143" ry="48" transform="rotate(-2 150 55)"
           fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>
</svg>
```

```css
.mkc { left: -4%; top: -16%; width: 108%; height: 132% }
```

## Зачёркивание старого балла

```html
<span style="position:relative;display:inline-block">81
  <svg class="sk" viewBox="0 0 200 40" preserveAspectRatio="none"
       style="position:absolute;left:-3%;top:0;width:106%;height:100%;color:#D7263D">
    <path d="M4 27 C 56 13, 142 31, 196 11" fill="none" stroke="currentColor"
          stroke-width="6" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
  </svg>
</span>
```

Без `position:relative` на родителе линия уезжает в угол кадра.

## Стрелка

```
path d="M14 8 C 70 40, 92 110, 62 176"
```

Те же атрибуты: `fill="none"`, `stroke="currentColor"`, `vector-effect="non-scaling-stroke"`.

## Правила

- `vector-effect="non-scaling-stroke"` обязателен, иначе толщина плывёт от растяжения.
- Цвет берётся через `currentColor`, так пометка совпадает с текстом.
- Кривые намеренно неровные. Ровная линия читается как графика, а нужна рука.
- Проверять число пометок: `h.count('class="mk')` должно дать 3.
