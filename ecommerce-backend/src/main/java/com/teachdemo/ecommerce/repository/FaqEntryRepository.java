package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.FaqEntry;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FaqEntryRepository extends JpaRepository<FaqEntry, Long> {

    List<FaqEntry> findByCategoryContainingIgnoreCaseOrQuestionContainingIgnoreCaseOrAnswerContainingIgnoreCase(
        String categoryKeyword,
        String questionKeyword,
        String answerKeyword);
}
