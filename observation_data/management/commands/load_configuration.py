import json
import os

from django.core.management.base import BaseCommand, CommandError
from observation_data.models import (
    Observatory,
    ExposureSettings,
    ObservatoryExposureSettings,
    ObservationType,
    Filter,
)


class Command(BaseCommand):
    help = "Loads the observatories, exposure settings and filters into the database."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the configuration file.")
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete the database before loading the configuration.",
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
        overwrite = options["overwrite"]
        delete = options["delete"]
        path = options["path"]
        if not os.path.exists(path):
            raise CommandError(f"File at {path} does not exist.")

        with open(path, "r") as f:
            data = json.load(f)

        obs_mapping = self.load_observatories(overwrite, delete, data)
        self.populate_exposure_settings(overwrite, delete, data)
        self.populate_filters(overwrite, delete, data, obs_mapping)

    def load_observatories(self, overwrite, delete, data):
        if delete:
            Observatory.objects.all().delete()

        created_observatories = []
        obs_mapping = {}
        for observatory in data["observatories"]:
            if (
                not overwrite
                and Observatory.objects.filter(name=observatory["name"]).exists()
            ):
                self.stdout.write(
                    f"Observatory {observatory['name']} already exists. Set --overwrite to overwrite."
                )
                continue
            self.stdout.write(f"Created observatory {observatory['name']}.")
            obs = Observatory.objects.create(
                name=observatory["name"],
                horizon_offset=observatory["horizon_offset"],
                min_stars=observatory["min_stars"],
                max_HFR=observatory["max_HFR"],
                max_guide_error=observatory["max_guide_error"],
            )
            created_observatories.append(obs)
            obs_mapping[observatory["name"]] = observatory["filters"]

        untouched_observatories = Observatory.objects.exclude(
            pk__in=[obs.pk for obs in created_observatories]
        )
        for obs in untouched_observatories:
            self.stdout.write(f"Observatory {obs.name} existed and was not changed.")

        return obs_mapping

    def populate_exposure_settings(self, overwrite, delete, data):
        if delete:
            ExposureSettings.objects.all().delete()
            ObservatoryExposureSettings.objects.all().delete()

        created_exposure_settings = []
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
                    self.stdout.write(
                        f"Exposure settings for {observation_type} at {obs.name} already exist. Set --overwrite to overwrite."
                    )
                    continue

                exposure_settings = ExposureSettings.objects.create(
                    gain=gain, offset=offset, binning=binning, subframe=subframe
                )
                created = ObservatoryExposureSettings.objects.create(
                    observatory=obs,
                    exposure_settings=exposure_settings,
                    observation_type=observation_type,
                )
                created_exposure_settings.append(created)
                self.stdout.write(
                    f"Created exposure settings for {observation_type} at {obs.name}."
                )

        untouched_exposure_settings = ObservatoryExposureSettings.objects.exclude(
            pk__in=[obs.pk for obs in created_exposure_settings]
        )
        for obs in untouched_exposure_settings:
            self.stdout.write(
                f"Exposure settings for {obs.observation_type} at {obs.observatory.name} existed and were not changed."
            )

    def populate_filters(self, overwrite, delete, data, observatory_mapping):
        if delete:
            Filter.objects.all().delete()

        created_filters = []
        for f in data["filters"]:
            filter_type = f["type"]
            if (
                not overwrite
                and Filter.objects.filter(filter_type=filter_type).exists()
            ):
                self.stdout.write(
                    f"Filter {filter_type} already exists. Set --overwrite to overwrite."
                )
                continue
            created = Filter.objects.create(
                filter_type=filter_type,
                moon_separation_angle=f["moon_separation_angle"],
                moon_separation_width=f["moon_separation_width"],
            )
            created_filters.append(created)
            self.stdout.write(f"Created filter {f['name']}.")
            for obs, filters in observatory_mapping.items():
                if f["name"] in filters:
                    obs = Observatory.objects.get(name=obs)
                    obs.filter_set.add(created)
                    self.stdout.write(
                        f"Added filter {f['name']} to observatory {obs.name}."
                    )

        untouched_filters = Filter.objects.exclude(
            pk__in=[f.pk for f in created_filters]
        )
        for f in untouched_filters:
            self.stdout.write(f"Filter {f.filter_type} existed and was not changed.")
