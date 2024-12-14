from django.forms.fields import Field
from django.forms import Widget
from django.utils.safestring import mark_safe
from django.db import models
from rest_framework.utils.formatting import camelcase_to_spaces


class _TURMInput(Widget):
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["name"] = name

    def _render_attrs(self, attr):
        attr = self.attrs | attr
        html_attrs = ""
        for key, value in attr.items():
            html_attrs += f'{key}="{value}" '
        return html_attrs

class _TURMNumericInput(_TURMInput):
    minimum = None
    maximum = None
    step = None

    def __init__(self, name: str, minimum=None, maximum=None, step=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.attrs["type"] = "text"
        self.attrs["inputmode"] = "numeric"
        if minimum: self.attrs["min"] = str(self.minimum)
        if maximum: self.attrs["max"] = str(self.maximum)
        if step: self.attrs["step"] = str(self.step)


class TURMIntegerInput(_TURMNumericInput):
    def __init__(self, name, minimum: int= None, maximum: int=None, step: int=None, *args, **kwargs):
        super().__init__(name, minimum, maximum, step, *args, **kwargs)
        self.attrs["oninput"] = "discard_input(event, this, '[^\\\\d*\\\\s*]')"

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(f'<input {self._render_attrs(attrs)}>')


class TURMFloatInput(_TURMNumericInput):
    def __init__(self, name, minimum: float = None, maximum: float = None, step: float = None, *args, **kwargs):
        super().__init__(name, minimum, maximum, step, *args, **kwargs)
        self.attrs["oninput"] = "discard_input(event, this, '[^\\\\d*\\\\s*\\\\.*]')" #todo restrict multiple dots

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(f'<input {self._render_attrs(attrs)}>')


class TURMChoiceInput(_TURMInput):
    pass

class TURMField(Field):
    def __init__(self, widget: _TURMInput, label_name: str= None, *args, **kwargs):
        super().__init__(widget=widget,label=label_name)

class TURMModelField(TURMField):
    def __init__(self, model_field: models.Field, label_name: str= None, *args, **kwargs):
        if label_name is None:
            label_name = model_field.name
        match type(model_field):
            case models.DecimalField:
                widget = TURMFloatInput(name=model_field.name, *args, **kwargs)
            case models.IntegerField:
                widget = TURMIntegerInput(name=model_field.name, *args, **kwargs)
            #case models.ManyToManyField:
                #widget = TURMChoiceInput(label_name=label_name, *args, **kwargs)
            case _:
                raise NotImplementedError(f"{type(model_field)} is not supported yet.")
        super().__init__(widget=widget,label=label_name)

"""
class TURMCheckboxSelectWidget(Widget):
    queryset = None
    extra_attribute_factory = None
    tooltip = None

    def __init__(
        self,
        queryset,
        extra_attribute_factory=None,
        tooltip=None,
        **kwargs,
    ):
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
            out += (
                f'<div class="{" tooltip_div" if self.tooltip is not None else ""}"> '
                f'<div class="multiple_choice_div">'
                f'<input type="checkbox" name="{name}" value="{q}" '
                f'id="id_{name}_{i}" {html_attributes} '
                f'{self.extra_attribute_factory(q) if self.extra_attribute_factory is not None else ""}>'
                f'<label for="id_{name}_{i}"> {q} </label>'
                f'{self._render_tooltip(f"id_{name}_{i}") if self.tooltip is not None else ""}'
                f'</div></div>'
            )
            i += 1
        out += "</div>"

        # print(Filter.objects.filter(observatories="TURMX"))
        # print(Observatory.objects.filter(filter_set__filter_type__icontains="R"))
        return mark_safe(out)

    def _render_tooltip(self, id):
        return f'<span class="tooltiptext" data-tip_for="{id}" style="display: none">{self.tooltip} text</span>'


class TURMNumericInputWidget(TextInput):
    def __init__(self, minimum=None, maximum=None, step=None, numeric_type=None):
        super().__init__()
        self.attrs.update({"inputmode": "numeric"})
        if minimum:
            self.attrs.update({"min": minimum})
        if maximum:
            self.attrs.update({"max": maximum})
        if step:
            self.attrs.update({"step": step})
        match numeric_type:
            case "integer":
                self.attrs.update({"data-suppressed": "\D"})
            case "decimal":
                self.attrs.update({"data-suppressed": "[^\d*\.+]"})
"""