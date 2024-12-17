from django.forms.fields import Field
from django.db import models
from observation_request.TURMInput import (_TURMInput, TURMIntegerInput, TURMFloatInput, TURMRadioInput,
                                           TURMCheckboxInput, TURMGridInput)


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
                return TURMCheckboxInput(name=model_field.name, choices=model_field.remote_field.model.objects.all(),
                                         *args, **kwargs)
            case models.ForeignKey:
                return TURMRadioInput(name=model_field.name, choices=model_field.remote_field.model.objects.all(),
                                      *args, **kwargs)
            case _:
                raise NotImplementedError(f"{type(model_field)} is not supported yet.")

    def add_dependencies(self, add_dependencies):
        self.widget.add_dependencies(add_dependencies)
        return self

    def add_dependency_generator(self, dependency_generator):
        self.widget.add_dependency_generator(dependency_generator)
        return self

    def add_on_click(self, func_call_generator):
        self.widget.add_on_click(func_call_generator)
        return self


class TURMModelField(TURMField):
    def __init__(self, model_field: models.Field, label_name: str= None, measurement_unit= None, *args, **kwargs):
        if label_name is None:
            label_name = model_field.name
        widget = self.model_field_to_input(model_field, measurement_unit, *args, **kwargs)
        super().__init__(widget=widget,label=label_name,*args, **kwargs)

class TURMSelectField(TURMField):
    def __init__(self, name, choices: list, label_name: str = None, *args, **kwargs):
        widget = TURMRadioInput(name=name, choices=choices)
        super().__init__(widget=widget, label_name=label_name, *args, **kwargs)

class TURMModelSelectField(TURMField):
    def __init__(self, model_field: models.Field, label_name: str = None, *args, **kwargs):
        widget = TURMRadioInput(name=model_field.name, choices=model_field.remote_field.model.objects.all())
        super().__init__(widget=widget, label_name=label_name, *args, **kwargs)


class TURMGridField(TURMField):
    def __init__(self, model_fields: list[models.Field], grid_dim = None, *args, **kwargs):
        sub_widgets = [self.model_field_to_input(field) for field in model_fields]
        widget = TURMGridInput(widgets=sub_widgets, grid_dim = grid_dim, *args, **kwargs)
        super().__init__(widget=widget, label_name="", *args, **kwargs)
