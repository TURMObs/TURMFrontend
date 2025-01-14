from datetime import datetime

from django.forms.fields import Field
from django.db import models
from observation_request.TURMInput import (_TURMInput, TURMIntegerInput, TURMFloatInput, TURMRadioInput,
                                           TURMCheckboxInput, TURMGridInput, TURMDateTimeInput, TURMDateInput,
                                           _TURMChoiceInput)


class TURMField(Field):
    def __init__(self, widget: _TURMInput, label_name: str= None, *args, **kwargs):
        super().__init__(widget=widget,label=label_name)

    def model_field_to_input(self, model_field, measurement_unit = None, *args, **kwargs):
        match type(model_field):
            case models.DecimalField:
                return TURMFloatInput(name=model_field.name, measurement_unit=measurement_unit,
                                      *args, **kwargs)
            case models.IntegerField:
                return TURMIntegerInput(name=model_field.name, measurement_unit=measurement_unit,
                                        *args, **kwargs)
            case models.ManyToManyField:
                self.required = False
                return TURMCheckboxInput(name=model_field.name, choices=[(str(name).title(),str(name)) for name in model_field.remote_field.model.objects.all()],
                                         *args, **kwargs)
            case models.ForeignKey:
                return TURMRadioInput(name=model_field.name, choices=[(str(name).title(),str(name)) for name in model_field.remote_field.model.objects.all()],
                                      *args, **kwargs)
            case models.DateTimeField:
                return TURMDateTimeInput(name=model_field.name, *args, **kwargs)
            case models.DateField:
                return TURMDateInput(name=model_field.name, *args, **kwargs)
            case _:
                raise NotImplementedError(f"{type(model_field)} is not supported yet.")

    def add_attrs(self, attr):
        self.widget.add_attrs(attr)
        return self

    def add_dependencies(self, add_dependencies):
        self.widget.add_dependencies(add_dependencies)
        return self

    def add_dependency_generator(self, dependency_generator):
        self.widget.add_dependency_generator(dependency_generator)
        return self

    def add_tooltip(self, tooltip):
        if isinstance(self.widget, _TURMChoiceInput):
            self.widget.add_tooltip(tooltip)
        return self

    def add_on_click(self, func_call_generator):
        self.widget.add_on_click(func_call_generator)
        return self


class TURMModelField(TURMField):
    def __init__(self, model_field: models.Field, label_name: str= None, measurement_unit= None, *args, **kwargs):
        if label_name is None:
            label_name = str(model_field.name).replace('_', ' ').title()
        widget = self.model_field_to_input(model_field, measurement_unit, *args, **kwargs)
        super().__init__(widget=widget,label_name=label_name,*args, **kwargs)

class TURMSelectField(TURMField):
    def __init__(self, name, choices: list[tuple[str, str]], label_name: str = None, *args, **kwargs):
        widget = TURMRadioInput(name=name, choices=choices)
        self.required = False
        super().__init__(widget=widget, label_name=label_name, *args, **kwargs)

class TURMModelSelectField(TURMField):
    def __init__(self, model_field: models.Field, label_name: str = None, *args, **kwargs):
        if label_name is None:
            label_name = str(model_field.name).title()
        self.required = False
        widget = TURMRadioInput(name=model_field.name, choices=[(str(name).title(),str(name)) for name in model_field.remote_field.model.objects.all()])
        super().__init__(widget=widget, label_name=label_name, *args, **kwargs)


class TURMGridField(TURMField):
    def __init__(self, model_fields: list[tuple[models.Field, str]], grid_dim = None, *args, **kwargs):
        sub_widgets = [(self.model_field_to_input(field[0]), field[1]) for field in model_fields]
        widget = TURMGridInput(widgets=sub_widgets, grid_dim = grid_dim, *args, **kwargs)
        super().__init__(widget=widget, label_name="", *args, **kwargs)

class TURMDateDuration(TURMField):
    def __init__(self, start: tuple[models.Field, str], end: tuple[models.Field, str] , *args, **kwargs):
        sub_widgets = [(TURMDateInput(start[0].name, minimum=datetime.date(datetime.now()),*args, **kwargs).add_on_value_changed(f'update_date_dependency(this)'), start[1]),
                       (TURMDateInput(end[0].name,*args, **kwargs), end[1])]
        widget = TURMGridInput(widgets=sub_widgets, grid_dim = (2,1), *args, **kwargs)
        super().__init__(widget=widget, label_name="", *args, **kwargs)

class TURMDateTimeDuration(TURMField):
    def __init__(self, start: tuple[models.Field, str], end: tuple[models.Field, str] , *args, **kwargs):
        sub_widgets = [(TURMDateTimeInput(start[0].name, minimum=datetime.now().strftime("%Y-%m-%dT23:59"),*args, **kwargs).add_on_value_changed(f'update_date_dependency(this)'), start[1]), #"%Y-%m-%dT%X"
                       (TURMDateTimeInput(end[0].name,*args, **kwargs), end[1])]
        widget = TURMGridInput(widgets=sub_widgets, grid_dim = (2,1), *args, **kwargs)
        super().__init__(widget=widget, label_name="", *args, **kwargs)
