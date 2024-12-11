from django.forms import Widget
from django.utils.safestring import mark_safe

from observation_data.models import Observatory, Filter


def attr_to_html(attr):
    out = ""
    for key, value in attr.items():
        out += f'{key}="{value}" '
    return out


class TURMCheckboxSelectWidget(Widget):
    queryset = None
    extra_attribute_factory = None
    tooltip = None

    def __init__(self, queryset, extra_attribute_factory=None, tooltip=None, **kwargs, ):
        super().__init__(**kwargs)
        if queryset is None:
            queryset = {}
        self.queryset = queryset
        self.extra_attribute_factory = extra_attribute_factory
        self.tooltip = tooltip

    def render(self, name, value, attrs=None, renderer=None):
        out = f'<div id="id_{name}" class="multiple_choice">'
        html_attributes = attr_to_html(self.attrs)
        i = 0

        for q in self.queryset:
            out += (f'<div class="{" tooltip_div" if self.tooltip is not None else ""}"> '
                    f'<div class="multiple_choice_div">'
                    f'<input type="checkbox" name="{name}" value="{q}" '
                    f'id="id_{name}_{i}" {html_attributes} '
                    f'{self.extra_attribute_factory(q) if self.extra_attribute_factory is not None else ""}>'
                    f'<label for="id_{name}_{i}"> {q} </label>'
                    f'{self._render_tooltip(f"id_{name}_{i}") if self.tooltip is not None else ""}'
                    f'</div></div>')
            i += 1
        out += '</div>'

        #print(Filter.objects.filter(observatories="TURMX"))
        #print(Observatory.objects.filter(filter_set__filter_type__icontains="R"))
        return mark_safe(out)

    def _render_tooltip(self, id):
        return f'<span class="tooltiptext" data-tip_for="{id}" style="display: none">{self.tooltip} text</span>'