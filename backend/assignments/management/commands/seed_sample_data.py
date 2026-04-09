from django.core.management.base import BaseCommand

from accounts.models import User
from rubrics.models import CriterionLevel, Rubric, RubricCriterion

RUBRIC_NAME = "Five-Paragraph Essay Rubric"
RUBRIC_DESCRIPTION = (
    "A standard rubric for evaluating five-paragraph essays across four key dimensions."
)

CRITERIA = [
    {
        "name": "Thesis & Argumentation",
        "order": 0,
        "levels": [
            (1, "No clear thesis"),
            (2, "Thesis present but weak"),
            (3, "Clear thesis with supporting arguments"),
            (4, "Strong, nuanced thesis with compelling arguments"),
        ],
    },
    {
        "name": "Evidence & Support",
        "order": 1,
        "levels": [
            (1, "No evidence provided"),
            (2, "Limited or irrelevant evidence"),
            (3, "Adequate evidence supporting claims"),
            (4, "Strong, well-integrated evidence from sources"),
        ],
    },
    {
        "name": "Organization & Structure",
        "order": 2,
        "levels": [
            (1, "No clear organization"),
            (2, "Some structure but inconsistent"),
            (3, "Clear intro, body, conclusion structure"),
            (4, "Sophisticated organization with smooth transitions"),
        ],
    },
    {
        "name": "Grammar & Mechanics",
        "order": 3,
        "levels": [
            (1, "Frequent errors impeding comprehension"),
            (2, "Noticeable errors but generally readable"),
            (3, "Few errors, generally polished"),
            (4, "Near-flawless grammar and mechanics"),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a sample five-paragraph essay rubric and print its ID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default=None,
            help="Email of the user who will own the rubric. "
            "Defaults to the first user found, or creates teacher@example.com.",
        )

    def handle(self, *args, **options):
        user = self._get_or_create_user(options["email"])

        if Rubric.objects.filter(user=user, name=RUBRIC_NAME).exists():
            rubric = Rubric.objects.get(user=user, name=RUBRIC_NAME)
            self.stdout.write(
                self.style.WARNING(
                    f"Rubric already exists: {RUBRIC_NAME} ({rubric.id})"
                )
            )
            return

        rubric = Rubric.objects.create(
            user=user,
            name=RUBRIC_NAME,
            description=RUBRIC_DESCRIPTION,
        )

        for criterion_data in CRITERIA:
            criterion = RubricCriterion.objects.create(
                rubric=rubric,
                name=criterion_data["name"],
                order=criterion_data["order"],
            )
            for level_order, (score, descriptor) in enumerate(criterion_data["levels"]):
                CriterionLevel.objects.create(
                    criterion=criterion,
                    order=level_order,
                    score=score,
                    descriptor=descriptor,
                )

        self.stdout.write(
            self.style.SUCCESS(f"Created rubric: {RUBRIC_NAME} ({rubric.id})")
        )

    def _get_or_create_user(self, email: str | None) -> User:
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with email {email} not found.")
                )
                raise

        first_user = User.objects.first()
        if first_user:
            self.stdout.write(f"Using existing user: {first_user.email}")
            return first_user

        user = User.objects.create_user(
            email="teacher@example.com",
            password="teacher123",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Created user: teacher@example.com (password: teacher123)"
            )
        )
        return user
