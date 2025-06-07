from collections import Counter
from typing import Any

from PyQt6.QtCore import QEvent
from PyQt6.QtCore import QObject
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFont
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from src.api.ApiBase import PreParsedApiResponse
from src.api.models.Map import Map
from src.api.models.MapVersionReview import MapVersionReview
from src.api.models.Mod import Mod
from src.api.models.ModVersionReview import ModVersionReview
from src.api.vaults_api import ReviewsApiConnector
from src.model.player import Player
from src.util import utctolocal
from src.vaults.starrating import StarRatingWidget

type VersionReview = MapVersionReview | ModVersionReview


def convert_review(dto_cls: type[Map | Mod], dto: dict[str, Any]) -> VersionReview:
    if dto_cls == Map:
        return MapVersionReview(**dto)
    elif dto_cls == Mod:
        return ModVersionReview(**dto)
    raise ValueError(f"Unexpected dto_cls: {dto_cls}")


class RatingDistribution:
    def __init__(self, reviews: list[VersionReview]) -> None:
        self.num_reviews = len(reviews)
        self.counts = Counter(review.score for review in reviews)

    def get_percentage(self, score: int) -> float:
        if self.num_reviews == 0:
            return 0
        return (self.counts[score] / self.num_reviews) * 100

    def get_count(self, score: int) -> int:
        return self.counts[score]

    def total_score(self) -> int:
        return sum(self.counts[score] * score for score in range(1, 6))

    def average_score(self) -> float:
        if self.num_reviews == 0:
            return 0.0
        return self.total_score() / self.num_reviews


class CommentWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        header_layout = QVBoxLayout()
        title_layout = QHBoxLayout()
        additional_info_layout = QHBoxLayout()

        self.nameLabel = QLabel()
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        self.nameLabel.setFont(name_font)

        self.deleteButton = QPushButton("Delete")
        self.editButton = QPushButton("Edit")
        title_layout.addWidget(self.nameLabel)
        title_layout.addStretch()
        title_layout.addWidget(self.editButton)
        title_layout.addWidget(self.deleteButton)

        header_layout.addLayout(title_layout)

        self.dateLabel = QLabel()
        self.dateLabel.setFixedWidth(200)

        self.versionLabel = QLabel()

        self.scoreLabel = QLabel()
        self.scoreLabel.setObjectName("starLabel")

        additional_info_layout.addWidget(self.dateLabel)
        additional_info_layout.addWidget(self.versionLabel)
        additional_info_layout.addWidget(self.scoreLabel)
        additional_info_layout.addStretch()
        header_layout.addLayout(additional_info_layout)
        layout.addLayout(header_layout)

        self.reviewText = QTextEdit()
        self.reviewText.setObjectName("reviewText")
        self.reviewText.setReadOnly(True)
        self.reviewText.setMaximumHeight(100)
        layout.addWidget(self.reviewText)

        widget.setLayout(layout)


class CommentWidget(QWidget):
    delete_request = pyqtSignal()
    edit_request = pyqtSignal()

    def __init__(
            self,
            player: Player,
            review: VersionReview | None = None,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.player = player
        self.review = review
        self.ui = CommentWidgetUI()
        self.ui.setupUi(self)
        if self.review is None:
            self.connect_signals()
        else:
            self.fill_ui()

    def is_own(self) -> bool:
        return (
            self.review is not None
            and self.review.player is not None
            and self.player.id == int(self.review.player.xd)
        )

    def connect_signals(self) -> None:
        self.ui.deleteButton.clicked.connect(self.delete_request.emit)
        self.ui.editButton.clicked.connect(self.edit_request.emit)

    def set_review(self, review: VersionReview) -> None:
        self.review = review

    def fill_ui(self) -> None:
        assert self.review is not None
        self.ui.nameLabel.setText(self.review.player.login if self.review.player else "Anonymous")
        self.ui.dateLabel.setText(utctolocal(self.review.create_time, "MMMM dd, yyyy hh:mm"))
        assert self.review.version is not None
        self.ui.versionLabel.setText(f"version {self.review.version.version}")
        self.ui.scoreLabel.setText(self.get_star_rating())
        self.ui.reviewText.setText(self.review.text)

        can_edit = self.is_own()
        self.ui.editButton.setVisible(can_edit)
        self.ui.deleteButton.setVisible(can_edit)

    def get_star_rating(self) -> str:
        assert self.review is not None
        full_stars = "★" * self.review.score
        empty_stars = "☆" * (5 - self.review.score)
        return f"{full_stars}{empty_stars} ({self.review.score}/5)"


class RatingBarWidgetUI:
    def setupUi(self, widget: QWidget) -> None:
        self.bars: dict[int, tuple[QProgressBar, QLabel]] = {}

        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        self.summaryLayout = QVBoxLayout()
        self.summaryLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.averageLabel = QLabel()
        self.averageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.averageLabel.setObjectName("averageReviewRatingLabel")
        self.summaryLayout.addWidget(self.averageLabel)

        self.reviewsCountLabel = QLabel()
        self.reviewsCountLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reviewsCountLabel.setObjectName("reviewRatingCountLabel")
        self.summaryLayout.addWidget(self.reviewsCountLabel)

        main_layout.addLayout(self.summaryLayout, stretch=1)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        title_label = QLabel("Rating Distribution")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        right_layout.addWidget(title_label)

        for score in range(5, 0, -1):
            row_layout = QHBoxLayout()

            star_label = QLabel(f"{score} {'★' if score == 1 else '★' * score}")
            star_label.setFixedWidth(80)
            row_layout.addWidget(star_label)

            progress_bar = QProgressBar()
            progress_bar.setObjectName("reviewRatingProgressBar")
            progress_bar.setRange(0, 100)
            progress_bar.setProperty("rating", str(score))

            row_layout.addWidget(progress_bar, 7)

            count_label = QLabel()
            count_label.setFixedWidth(40)
            count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(count_label)
            self.bars[score] = (progress_bar, count_label)

            right_layout.addLayout(row_layout)

        main_layout.addLayout(right_layout, stretch=3)


class RatingBarWidget(QWidget):
    def __init__(self, distribution: RatingDistribution, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.distribution = distribution
        self.ui = RatingBarWidgetUI()
        self.ui.setupUi(self)
        self.fill_ui()

    def fill_ui(self) -> None:
        average = self.distribution.average_score()
        self.ui.averageLabel.setText(f"{average:.1f}")
        self.ui.reviewsCountLabel.setText(f"{self.distribution.num_reviews} reviews")
        star_rating = StarRatingWidget(
            rating=average,
            max_rating=5,
            star_size=20,
            star_color_filled=QColor("#4CAF50"),
        )
        self.ui.summaryLayout.insertWidget(1, star_rating)

        for score, (bar, count) in self.ui.bars.items():
            bar.setValue(int(self.distribution.get_percentage(score)))
            count.setText(f"{self.distribution.get_count(score)}")


class ReviewDialogUi:
    def setupUi(self, widget: QWidget) -> None:
        widget.setWindowTitle("Leave a Review")

        rating_label = QLabel("Rating:")
        font = rating_label.font()
        font.setBold(True)
        rating_label.setFont(font)
        comment_label = QLabel("Your Review:")
        comment_label.setFont(font)

        self.commentTextEdit = QTextEdit()
        self.commentTextEdit.setPlaceholderText("(Optional) Add a comment...")

        self.submitButton = QPushButton("Submit Review")

        main_layout = QVBoxLayout(widget)
        main_layout.addWidget(rating_label)

        self.ratingLayout = QHBoxLayout()
        self.ratingLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        main_layout.addLayout(self.ratingLayout)

        main_layout.addWidget(comment_label)
        main_layout.addWidget(self.commentTextEdit)
        main_layout.addWidget(self.submitButton)


class ReviewDialog(QDialog):
    review_submitted = pyqtSignal(object)

    def __init__(
            self,
            item: Map | Mod,
            player: Player,
            review: VersionReview | None = None,
            parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.player = player
        if review is None:
            klass = MapVersionReview if isinstance(item, Map) else ModVersionReview
            self.review = klass.model_construct(id="null", score=0, text="", version=item.version)
        else:
            self.review = review
        self._hovered_rating = 0

        self.star_rating = StarRatingWidget(self.review.score)
        self.star_rating.setMouseTracking(True)
        self.star_rating.installEventFilter(self)

        self.reviews_api = ReviewsApiConnector()
        self.reviews_api.data_ready.connect(self.on_reviews_data)

        self.ui = ReviewDialogUi()
        self.init_ui()

    def on_reviews_data(self, message: PreParsedApiResponse) -> None:
        self.setEnabled(True)
        if not (data := message["data"]):
            return
        assert isinstance(data, list)
        self.review = convert_review(type(self.item), data[0])
        self.update_appearance()

    def start(self) -> None:
        if self.review.xd == "null":
            self.reviews_api.request_review_by_player(self.item, self.player)
            self.setEnabled(False)
        self.exec()

    def init_ui(self) -> None:
        self.ui.setupUi(self)
        self.ui.ratingLayout.addWidget(self.star_rating)
        self.ui.submitButton.clicked.connect(self.submit_review)
        self.update_appearance()

    def update_appearance(self) -> None:
        self.star_rating.set_rating(self.review.score)
        self.ui.commentTextEdit.setText(self.review.text)
        cursor = self.ui.commentTextEdit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.ui.commentTextEdit.setTextCursor(cursor)

    def _handle_mouse_over_star(self, event: QEvent) -> None:
        match event.type():
            case QEvent.Type.MouseMove:
                assert isinstance(event, QMouseEvent)
                x = event.pos().x()
                star_width = self.star_rating.star_size
                hovered_rating = (x + star_width) // star_width
                self.star_rating.set_rating(hovered_rating)
                self._hovered_rating = hovered_rating
            case QEvent.Type.MouseButtonRelease:
                assert isinstance(event, QMouseEvent)
                if event.button() == Qt.MouseButton.LeftButton:
                    self.review.score = self._hovered_rating
            case QEvent.Type.Leave:
                self.star_rating.set_rating(self.review.score)
            case _:
                ...

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]  # noqa: E501
        if obj == self.star_rating and event is not None:
            self._handle_mouse_over_star(event)
        return super().eventFilter(obj, event)

    def submit_review(self) -> None:
        self.review.text = self.ui.commentTextEdit.toPlainText()
        self.review_submitted.emit(self.review)
