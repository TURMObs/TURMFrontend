import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from observation_data.models import (
    Observatory,
    ExposureSettings,
    ObservatoryExposureSettings,
    ObservationType,
    Filter,
    DefaultRequestSettings,
)


class Command(BaseCommand):
    help = "Loads the observatories, exposure settings and filters into the database."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the configuration file.")
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete objects that are no longer specified by the configuration.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite the existing configuration.",
        )

    def handle(self, *args, **options):
        """
        This command adds the observatories, exposure settings and filters to the database.
        """
        overwrite = options["overwrite"] or options["delete"]
        delete = options["delete"]
        path = options["path"]
        if not os.path.exists(path):
            raise CommandError(f"File at {path} does not exist.")

        with open(path, "r") as f:
            data = json.load(f)

        if delete:
            try:
                ObservatoryExposureSettings.objects.all().delete()
            except IntegrityError as e:
                self.stdout.write(f"Error deleting existing data: {e}")

            try:
                for obs in Observatory.objects.all():
                    obs.filter_set.clear()
            except IntegrityError as e:
                self.stdout.write(f"Error deleting existing data: {e}")

        obs_mapping, untouched_observatories = self.load_observatories(
            overwrite, data, delete
        )
        untouched_exposure_settings = self.populate_exposure_settings(
            overwrite, data, delete
        )
        untouched_filters = self.populate_filters(overwrite, data, obs_mapping, delete)

        self.populate_default_request_settings(overwrite, data)

        if delete:
            try:
                untouched_exposure_settings.delete()
                untouched_filters.delete()
                untouched_observatories.delete()
            except IntegrityError as e:
                self.stdout.write(f"Error deleting existing data: {e}")

    def load_observatories(self, overwrite, data, delete):
        created_observatories = []
        skipped_overwrite = []
        obs_mapping = {}
        for observatory in data["observatories"]:
            if (
                not overwrite
                and Observatory.objects.filter(name=observatory["name"]).exists()
            ):
                skipped_overwrite.append(observatory["name"])
                self.stdout.write(
                    f"Observatory {observatory['name']} already exists. Set --overwrite to overwrite."
                )
                continue

            obs, created = Observatory.objects.update_or_create(
                name=observatory["name"],
                defaults={
                    "horizon_offset": observatory["horizon_offset"],
                    "min_stars": observatory["min_stars"],
                    "max_HFR": observatory["max_HFR"],
                    "max_guide_error": observatory["max_guide_error"],
                },
            )
            created_observatories.append(obs)
            obs_mapping[observatory["name"]] = observatory["filters"]

            if not created:
                self.stdout.write(
                    f"Updated configuration for observatory {observatory['name']}."
                )
            else:
                self.stdout.write(f"Created observatory {observatory['name']}.")

        untouched_observatories = Observatory.objects.exclude(
            pk__in=[obs.pk for obs in created_observatories]
        )
        for obs in untouched_observatories:
            if obs.name not in skipped_overwrite and not delete:
                self.stdout.write(
                    f"Observatory {obs.name} existed and was not changed."
                )

        return obs_mapping, untouched_observatories

    def populate_exposure_settings(self, overwrite, data, delete):
        created_exposure_settings = []
        skipped_overwrite = []
        for observatory in data["observatories"]:
            observatory_name = observatory["name"]
            for settings in observatory["exposure_settings"]:
                if not Observatory.objects.filter(name=observatory_name).exists():
                    self.stdout.write(
                        f"Observatory {observatory_name} does not exist. Skipping exposure settings."
                    )
                    continue

                obs = Observatory.objects.get(name=observatory_name)
                observation_type = settings["type"].capitalize()
                try:
                    observation_type = ObservationType(observation_type)
                except ValueError:
                    self.stdout.write(
                        f"Exposure setting references unknown observation type {observation_type}. Skipping."
                    )
                    continue

                gain, offset, binning, subframe = (
                    settings["gain"],
                    settings["offset"],
                    settings["binning"],
                    settings["subframe"],
                )

                if (
                    not overwrite
                    and ObservatoryExposureSettings.objects.filter(
                        observatory=obs, observation_type=observation_type
                    ).exists()
                ):
                    skipped_overwrite.append((obs.name, observation_type))
                    self.stdout.write(
                        f"Exposure settings for {observation_type} at {obs.name} already exist. Set --overwrite to overwrite."
                    )
                    continue
                if not ExposureSettings.objects.filter(
                    gain=gain, offset=offset, binning=binning, subframe=subframe
                ).exists():
                    exposure_settings = ExposureSettings.objects.create(
                        gain=gain, offset=offset, binning=binning, subframe=subframe
                    )
                else:
                    exposure_settings = ExposureSettings.objects.filter(
                        gain=gain, offset=offset, binning=binning, subframe=subframe
                    ).first()
                obj, created = ObservatoryExposureSettings.objects.update_or_create(
                    observatory=obs,
                    observation_type=observation_type,
                    defaults={"exposure_settings": exposure_settings},
                )
                created_exposure_settings.append(obj)
                if not created:
                    self.stdout.write(
                        f"Updated configuration of exposure settings for {observation_type} at {obs.name}."
                    )
                else:
                    self.stdout.write(
                        f"Created exposure settings for {observation_type} at {obs.name}."
                    )

        untouched_exposure_settings = ObservatoryExposureSettings.objects.exclude(
            pk__in=[obs.pk for obs in created_exposure_settings]
        )
        for obs in untouched_exposure_settings:
            if (
                obs.observatory.name,
                obs.observation_type,
            ) not in skipped_overwrite and not delete:
                self.stdout.write(
                    f"Exposure settings for {obs.observation_type} at {obs.observatory.name} existed and were not changed."
                )

        return untouched_exposure_settings

    def populate_filters(self, overwrite, data, observatory_mapping, delete):
        created_filters = []
        skipped_overwrite = []
        for f in data["filters"]:
            filter_type = f["type"]
            if (
                not overwrite
                and Filter.objects.filter(filter_type=filter_type).exists()
            ):
                skipped_overwrite.append(filter_type)
                self.stdout.write(
                    f"Filter {filter_type} already exists. Set --overwrite to overwrite."
                )
                continue
            obj, created = Filter.objects.update_or_create(
                filter_type=filter_type,
                defaults={
                    "moon_separation_angle": f["moon_separation_angle"],
                    "moon_separation_width": f["moon_separation_width"],
                },
            )
            created_filters.append(obj)
            for obs, filters in observatory_mapping.items():
                if f["name"] in filters:
                    obs = Observatory.objects.get(name=obs)
                    obs.filter_set.add(obj)
                    self.stdout.write(
                        f"Added filter {f['name']} to observatory {obs.name}."
                    )
            if not created:
                self.stdout.write(f"Updated configuration of filter {f['name']}.")
            else:
                self.stdout.write(f"Created filter {f['name']}.")

        untouched_filters = Filter.objects.exclude(
            pk__in=[f.pk for f in created_filters]
        )
        for f in untouched_filters:
            if f.filter_type not in skipped_overwrite and not delete:
                self.stdout.write(
                    f"Filter {f.filter_type} existed and was not changed."
                )
        return untouched_filters

    def populate_default_request_settings(self, overwrite, data):
        if not overwrite and DefaultRequestSettings.objects.filter(id=0).exists():
            self.stdout.write(
                "Default request settings already exists. Set --overwrite to overwrite."
            )
            return None
        if not DefaultRequestSettings.objects.filter(id=0).exists():
            self.stdout.write("Created Default request settings.")

        settings, _ = DefaultRequestSettings.objects.update_or_create(
            id=0, defaults={"settings": data["request_settings_defaults"]}
        )
